from uuid import UUID
from app.tasks.worker import ingest_document_task


async def ingest_document(
        document_id: UUID,
        version_id: UUID,
        s3_path: str,
        tenant_id: UUID,
) -> None:
    """Enqueues the document ingestion task."""
    ingest_document_task.delay(
        document_id_str=str(document_id),
        version_id_str=str(version_id),
        s3_path=s3_path,
        tenant_id_str=str(tenant_id),
    )
