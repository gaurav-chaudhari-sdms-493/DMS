import logging
from uuid import UUID
from ..tasks.worker import ingest_document_task

logger = logging.getLogger(__name__)


async def ingest_document(
        document_id: UUID,
        version_id: UUID,
        s3_path: str,
        tenant_id: UUID,
) -> None:
    """Enqueues the document ingestion task with local asyncio fallback."""
    try:
        res = ingest_document_task.delay(
            document_id_str=str(document_id),
            version_id_str=str(version_id),
            s3_path=s3_path,
            tenant_id_str=str(tenant_id),
        )
        logger.info(f"Enqueued Celery task {res.id} for document {document_id}")
    except Exception as e:
        logger.error(f"Failed to enqueue Celery task for document {document_id}: {e}. Running background asyncio task.")
        import asyncio
        from ..tasks.worker import _ingest_document_task_async
        asyncio.create_task(_ingest_document_task_async(str(document_id), str(version_id), s3_path, str(tenant_id)))