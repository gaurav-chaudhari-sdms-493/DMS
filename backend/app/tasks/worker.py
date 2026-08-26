import asyncio
import hashlib
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
from ..services.config_service import get_int, get_float
from ..services.extraction_archive_service import get_cached_ocr, record_ocr
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
        file_hash = hashlib.sha256(file_bytes).hexdigest()

        # 2. OCR — TS3: an unchanged file (by content hash) under the same
        # OCR engine is never re-OCR'd; reprocessing the same upload after a
        # chunking/parsing fix replays the archived response for free.
        pages = None
        try:
            async with AsyncSessionLocal() as cache_db:
                pages = await get_cached_ocr(cache_db, file_hash, settings.ai_ocr_provider)
        except Exception as cache_err:
            logger.warning(f"TS3 OCR cache lookup failed for {document_id_str}: {cache_err}")

        if pages is not None:
            logger.info(f"TS3 OCR cache hit for document {document_id_str} (hash {file_hash[:12]}...)")
        else:
            ocr = get_ocr_provider()
            pages = await ocr.extract_pages(file_bytes, filename)
            try:
                async with AsyncSessionLocal() as cache_db:
                    await record_ocr(cache_db, file_hash, settings.ai_ocr_provider, pages)
                    await cache_db.commit()
            except Exception as cache_err:
                logger.warning(f"TS3 OCR cache write failed for {document_id_str}: {cache_err}")

        # 3. Chunk
        chunk_size = await get_int("chunk_size_tokens", 512)
        chunk_overlap = await get_int("chunk_overlap_tokens", 64)
        chunker = TextChunker(chunk_size=chunk_size, chunk_overlap=chunk_overlap)
        chunks = chunker.chunk_pages(pages)

        if not chunks or all(p.get("extraction_failed") for p in pages):
            raise ValueError(
                "No readable text could be extracted from this document. "
                "It may be a scanned image requiring an OCR provider "
                "(set AI_OCR_PROVIDER=gcv or llamaparse)."
            )

        # TS2 — data-loss audit: does every word OCR read survive into the
        # chunks about to be stored (the search/chat/viewer-facing surface)?
        # Best-effort, same as every other optional pipeline stage here —
        # a failure here must never block ingestion.
        data_loss_result = None
        try:
            from app.services.data_loss_audit import audit_pages_vs_chunks
            data_loss_result = audit_pages_vs_chunks(pages, [c.content for c in chunks])
            if not data_loss_result.passed:
                logger.warning(
                    f"TS2 data-loss audit: document {document_id_str} lost "
                    f"{data_loss_result.missing_count}/{data_loss_result.total_words} words "
                    f"({data_loss_result.loss_ratio:.2%}) between OCR and stored chunks"
                )
        except Exception as audit_err:
            logger.warning(f"TS2 data-loss audit skipped for document {document_id_str}: {audit_err}")

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
                    extraction_confidence = await get_float("default_extraction_confidence", 0.9)
                    for key, value in meta_dict.items():
                        db_meta = MetadataItem(
                            document_id=document_id,
                            key=key,
                            value=value if isinstance(value, (dict, list)) else {"v": value},
                            source="llm",
                            confidence_score=extraction_confidence,
                        )
                        db.add(db_meta)

                    if meta_dict.get("title"):
                        stmt = select(Document).where(Document.id == document_id)
                        res = await db.execute(stmt)
                        doc = res.scalar_one_or_none()
                        if doc and doc.title == "Unknown":
                            doc.title = meta_dict["title"]
                            doc.doc_type = meta_dict.get("document_type")

                # 5b. T23 — classification stage, unconditional (runs regardless of
                # whether VLM extraction is even enabled). Persists the result on
                # the document instead of the ad-hoc unpersisted match T22 used to
                # do inline. A savepoint isolates it, same reasoning as T22 below.
                template = None
                try:
                    from app.services.classification_service import classify_document
                    sample_text = pages[0].get("text", "") if pages else ""
                    async with db.begin_nested():
                        classified_doc = await classify_document(db, tenant_id, document_id, sample_text)
                    if classified_doc.matched_template_id:
                        from app.models.template import Template as TemplateModel
                        template = await db.get(TemplateModel, classified_doc.matched_template_id)
                except Exception as classify_err:
                    logger.warning(f"T23 classification skipped for document {document_id}: {classify_err}")

                # 5c. T22 — VLM extraction against the matched template, if any.
                # Best-effort and non-blocking: a savepoint isolates it so a failure
                # here never aborts the chunk/metadata commit above (search must
                # never wait on this, Section 3.5).
                if template:
                    try:
                        from app.pipeline.vlm_extraction import extract_facts_for_document
                        async with db.begin_nested():
                            facts_count = await extract_facts_for_document(
                                db, tenant_id, document_id, version_id,
                                file_bytes, filename, pages, template,
                            )
                        if facts_count:
                            logger.info(
                                f"T22 VLM extraction wrote {facts_count} facts for "
                                f"document {document_id} against template "
                                f"{template.form_type}/{template.era_label}"
                            )
                    except Exception as vlm_err:
                        logger.warning(f"T22 VLM extraction skipped for document {document_id}: {vlm_err}")

                # Update status to indexed
                stmt = select(Document).where(Document.id == document_id)
                res = await db.execute(stmt)
                doc = res.scalar_one_or_none()
                if doc:
                    doc.status = "indexed"
                    # T76 — every document gets these, not just template
                    # matches (unlike doc_dg_pages, which only T22 writes to).
                    doc.pages_total_count = len(pages)
                    doc.pages_failed_count = sum(1 for p in pages if p.get("extraction_failed"))
                    if data_loss_result:
                        doc.data_loss_words_missing = data_loss_result.missing_count
                        doc.data_loss_details = (
                            {"loss_ratio": data_loss_result.loss_ratio, "missing_sample": data_loss_result.missing_sample}
                            if data_loss_result.missing_count > 0 else None
                        )

        try:
            from app.services.cache_service import invalidate_tenant_cache
            await invalidate_tenant_cache(tenant_id_str)
        except Exception as cache_err:
            logger.warning(f"Tenant cache invalidation warning for {tenant_id_str}: {cache_err}")

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


celery_app.conf.beat_schedule = {
    "cleanup-30-day-trashed-items": {
        "task": "app.tasks.cleanup_trashed_items_task",
        "schedule": 86400.0,  # Run daily (every 24 hours)
    },
}


@celery_app.task(name="app.tasks.ingest_document_task")
def ingest_document_task(document_id_str: str, version_id_str: str, s3_path: str, tenant_id_str: str) -> None:
    import asyncio
    asyncio.run(_ingest_document_task_async(document_id_str, version_id_str, s3_path, tenant_id_str))


async def _cleanup_trashed_items_async() -> None:
    from app.services.document_service import cleanup_expired_trashed_items
    retention_days = await get_int("trash_retention_days", 30)
    async with AsyncSessionLocal() as db:
        await cleanup_expired_trashed_items(db, retention_days=retention_days)


@celery_app.task(name="app.tasks.cleanup_trashed_items_task")
def cleanup_trashed_items_task() -> None:
    import asyncio
    asyncio.run(_cleanup_trashed_items_async())