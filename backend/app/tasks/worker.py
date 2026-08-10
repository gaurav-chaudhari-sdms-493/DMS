import asyncio
import json
import logging
import os
from uuid import UUID

from celery import Celery
from sqlalchemy import select, delete, text

from ..ai.base import Message
from ..ai.factory import get_embed_provider, get_llm_provider
from ..database import AsyncSessionLocal
from ..models.chunk import Chunk as DBChunk
from ..models.document import Document
from ..models.metadata_item import MetadataItem
from ..ocr.factory import get_ocr_provider
from ..pipeline.chunker import TextChunker
from ..services.storage_service import download_file
from ..config import settings

celery_app = Celery(
    "worker",
    broker=settings.redis_url,
    backend=settings.redis_url,
    broker_connection_retry_on_startup=True
)

logger = logging.getLogger(__name__)


async def extract_metadata(text: str) -> dict:
    prompt = f"""
Extract the following metadata from the text below. 
Return ONLY a valid JSON object with these keys: "title", "author", "date", "document_type", "key_topics" (list of strings), "summary".
If a field is not found, use null or empty list.

Text snippet:
{text[:4000]}
"""
    try:
        llm = get_llm_provider()
        resp = await llm.complete([Message(role="user", content=prompt)])

        # simple cleanup for markdown json blocks
        clean_resp = resp.strip()
        if clean_resp.startswith("```json"):
            clean_resp = clean_resp[7:]
        if clean_resp.endswith("```"):
            clean_resp = clean_resp[:-3]
        return json.loads(clean_resp.strip())
    except Exception as e:
        logger.error(f"Metadata extraction failed: {e}")
        return {}


async def _ingest_document_task_async(document_id_str: str, version_id_str: str, s3_path: str, tenant_id_str: str) -> None:
    """Celery task for full ingestion pipeline with ACID Atomicity: OCR → chunk → embed → store."""
    from app.database import engine
    try:
        document_id = UUID(document_id_str)
        version_id = UUID(version_id_str)
        tenant_id = UUID(tenant_id_str)

        # 1. Download file
        file_bytes = await download_file(s3_path)
        filename = os.path.basename(s3_path)

        # 2. OCR
        ocr = get_ocr_provider()
        pages = await ocr.extract_pages(file_bytes, filename)

        # 3. Chunk
        chunker = TextChunker()
        chunks = chunker.chunk_pages(pages)

        if not chunks or all(p.get("extraction_failed") for p in pages):
            raise ValueError(
                "No readable text could be extracted from this document. "
                "It may be a scanned image requiring an OCR provider "
                "(set AI_OCR_PROVIDER=gcv or llamaparse)."
            )

        # 4. Embed chunks (batched for local BGE-M3 model / API providers)
        embed_provider = get_embed_provider()
        EMBED_BATCH_SIZE = 20
        EMBED_BATCH_DELAY = 0.1
        MAX_RETRIES = 3

        chunk_texts = [c.content for c in chunks]
        embeddings = []
        for batch_start in range(0, len(chunk_texts), EMBED_BATCH_SIZE):
            batch = chunk_texts[batch_start:batch_start + EMBED_BATCH_SIZE]
            for attempt in range(MAX_RETRIES):
                try:
                    batch_embeddings = await embed_provider.embed(batch)
                    embeddings.extend(batch_embeddings)
                    break
                except Exception as embed_err:
                    is_rate_limit = "429" in str(embed_err)
                    try:
                        import cohere as _cohere
                        is_rate_limit = is_rate_limit or isinstance(embed_err, _cohere.TooManyRequestsError)
                    except Exception:
                        pass
                    if is_rate_limit and attempt < MAX_RETRIES - 1:
                        wait = 2 ** attempt * 5
                        logger.warning(f"Embed rate limited (attempt {attempt+1}/{MAX_RETRIES}), retrying in {wait}s...")
                        await asyncio.sleep(wait)
                    else:
                        raise
            if batch_start + EMBED_BATCH_SIZE < len(chunk_texts):
                await asyncio.sleep(EMBED_BATCH_DELAY)

        # 5. Extract metadata
        full_text = " ".join([p.get("text", "") for p in pages])
        meta_dict = await extract_metadata(full_text)

        # 6. ATOMIC DATABASE TRANSACTION (All-or-Nothing Commit)
        # All database writes (chunks, metadata, document status) occur inside a single atomic transaction.
        async with AsyncSessionLocal() as db:
            async with db.begin():
                await db.execute(text("SELECT set_config('app.current_tenant_id', :t, false)"), {"t": tenant_id_str})
                # Purge any pre-existing partial chunks or metadata for this version/document
                await db.execute(delete(DBChunk).where(DBChunk.version_id == version_id))
                await db.execute(delete(MetadataItem).where(MetadataItem.document_id == document_id))

                # Insert chunks
                for idx, chunk in enumerate(chunks):
                    db_chunk = DBChunk(
                        document_id=document_id,
                        version_id=version_id,
                        tenant_id=tenant_id,
                        content=chunk.content,
                        page_number=chunk.page_number,
                        chunk_index=chunk.chunk_index,
                        embedding=embeddings[idx],
                        chunk_metadata={"token_count": chunk.token_count, "bbox": chunk.bbox},
                        s3_path=s3_path
                    )
                    db.add(db_chunk)

                # Insert metadata items
                if meta_dict:
                    for key, value in meta_dict.items():
                        db_meta = MetadataItem(
                            document_id=document_id,
                            key=key,
                            value=value if isinstance(value, (dict, list)) else {"v": value},
                            source="llm",
                            confidence_score=0.9,
                        )
                        db.add(db_meta)

                    if meta_dict.get("title"):
                        stmt = select(Document).where(Document.id == document_id)
                        res = await db.execute(stmt)
                        doc = res.scalar_one_or_none()
                        if doc and doc.title == "Unknown":
                            doc.title = meta_dict["title"]
                            doc.doc_type = meta_dict.get("document_type")

                # Update status to indexed
                stmt = select(Document).where(Document.id == document_id)
                res = await db.execute(stmt)
                doc = res.scalar_one_or_none()
                if doc:
                    doc.status = "indexed"

        from app.services.cache_service import invalidate_tenant_cache
        await invalidate_tenant_cache(tenant_id_str)

        logger.info(f"Successfully ingested document {document_id} with {len(chunks)} chunks and 1024d embeddings.")

    except Exception as e:
        logger.error(f"Ingestion failed for document {document_id_str}: {e}", exc_info=True)
        # ATOMIC CLEANUP & FAILURE RECORDING
        # If any operation fails, roll back all DB writes, purge orphaned rows, and mark document as failed.
        async with AsyncSessionLocal() as db_fail:
            async with db_fail.begin():
                try:
                    await db_fail.execute(text("SELECT set_config('app.current_tenant_id', :t, false)"), {"t": tenant_id_str})
                    document_id = UUID(document_id_str)
                    version_id = UUID(version_id_str)
                    await db_fail.execute(delete(DBChunk).where(DBChunk.version_id == version_id))
                    await db_fail.execute(delete(MetadataItem).where(MetadataItem.document_id == document_id))

                    stmt = select(Document).where(Document.id == document_id)
                    res = await db_fail.execute(stmt)
                    doc = res.scalar_one_or_none()
                    if doc:
                        doc.status = "failed"
                except Exception as inner_e:
                    logger.error(f"Failed to record ingestion failure status for {document_id_str}: {inner_e}")
    finally:
        await engine.dispose()


@celery_app.task(name="app.tasks.ingest_document_task")
def ingest_document_task(document_id_str: str, version_id_str: str, s3_path: str, tenant_id_str: str) -> None:
    import asyncio
    asyncio.run(_ingest_document_task_async(document_id_str, version_id_str, s3_path, tenant_id_str))