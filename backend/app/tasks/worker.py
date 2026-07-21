import json
import logging
import os
from uuid import UUID

from celery import Celery
from sqlalchemy import select

from app.ai.base import Message
from app.ai.factory import get_embed_provider, get_llm_provider
from app.database import AsyncSessionLocal
from app.models.chunk import Chunk as DBChunk
from app.models.document import Document
from app.models.metadata_item import MetadataItem
from app.ocr.factory import get_ocr_provider
from app.pipeline.chunker import TextChunker
from app.services.storage_service import download_file
from app.config import settings

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


@celery_app.task(name="app.tasks.ingest_document_task")
async def ingest_document_task(document_id_str: str, version_id_str: str, s3_path: str, tenant_id_str: str) -> None:
    """Celery task for the full ingestion pipeline: OCR → chunk → embed → store."""
    document_id = UUID(document_id_str)
    version_id = UUID(version_id_str)
    tenant_id = UUID(tenant_id_str)

    async with AsyncSessionLocal() as db:
        try:
            # 1. Download file
            file_bytes = await download_file(s3_path)
            filename = os.path.basename(s3_path)

            # 2. OCR
            ocr = get_ocr_provider()
            pages = await ocr.extract_pages(file_bytes, filename)

            # 3. Chunk
            chunker = TextChunker()
            chunks = chunker.chunk_pages(pages)

            if not chunks:
                raise ValueError("No text found in document.")

            # 4. Embed chunks
            embed_provider = get_embed_provider()
            embeddings = await embed_provider.embed([c.content for c in chunks])

            # 5. Insert chunks
            for idx, chunk in enumerate(chunks):
                db_chunk = DBChunk(
                    document_id=document_id,
                    version_id=version_id,
                    content=chunk.content,
                    page_number=chunk.page_number,
                    chunk_index=chunk.chunk_index,
                    embedding=embeddings[idx]
                )
                db.add(db_chunk)

            # 6. Extract metadata
            full_text = " ".join([p.get("text", "") for p in pages])
            meta_dict = await extract_metadata(full_text)

            # 7. Insert metadata
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

            # 8. Update status
            stmt = select(Document).where(Document.id == document_id)
            res = await db.execute(stmt)
            doc = res.scalar_one_or_none()
            if doc:
                doc.status = "indexed"

            await db.commit()

        except Exception as e:
            logger.error(f"Ingestion failed for {document_id}: {e}")
            async with AsyncSessionLocal() as db_fail:
                try:
                    stmt = select(Document).where(Document.id == document_id)
                    res = await db_fail.execute(stmt)
                    doc = res.scalar_one_or_none()
                    if doc:
                        doc.status = "failed"
                    await db_fail.commit()
                except Exception as inner_e:
                    logger.error(f"Failed to update document status to 'failed': {inner_e}")