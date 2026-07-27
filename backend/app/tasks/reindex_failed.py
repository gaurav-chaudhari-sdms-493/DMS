import asyncio
import logging
from sqlalchemy import select
from app.database import AsyncSessionLocal
from app.models.document import Document
from app.models.document_version import DocumentVersion
from app.tasks.worker import ingest_document_task

logger = logging.getLogger(__name__)

async def reindex_all_failed_documents():
    """Find all documents with status='failed' and trigger Celery re-ingestion."""
    async with AsyncSessionLocal() as db:
        stmt = select(Document).where(Document.status == "failed", Document.is_trashed == False)
        res = await db.execute(stmt)
        failed_docs = res.scalars().all()
        
        print(f"Found {len(failed_docs)} failed documents to re-index.")
        reindexed_count = 0
        
        for doc in failed_docs:
            if not doc.current_version_id:
                continue
            
            v_res = await db.execute(select(DocumentVersion).where(DocumentVersion.id == doc.current_version_id))
            version = v_res.scalar_one_or_none()
            if not version or not version.s3_path:
                continue

            print(f"Re-queuing document '{doc.title}' (ID: {doc.id}) for ingestion...")
            ingest_document_task.delay(
                document_id_str=str(doc.id),
                version_id_str=str(doc.current_version_id),
                s3_path=version.s3_path,
                tenant_id_str=str(doc.tenant_id),
            )
            reindexed_count += 1
            
        print(f"Successfully re-queued {reindexed_count} documents for ingestion.")

if __name__ == "__main__":
    asyncio.run(reindex_all_failed_documents())
