"""Ingestion entry point.

The actual pipeline (OCR → chunk → embed → store) lives in
app/tasks/worker.py and runs inside a Celery worker. This module only
enqueues the job so that the HTTP upload request returns immediately.
"""

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
    """Queue a document for background ingestion."""
    ingest_document_task.delay(
        document_id_str=str(document_id),
        version_id_str=str(version_id),
        s3_path=s3_path,
        tenant_id_str=str(tenant_id),
    )
    logger.info("Queued document %s (version %s) for ingestion", document_id, version_id)