import hashlib
import uuid
import logging
from fastapi import UploadFile, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from uuid import UUID

from ..models.document import Document
from ..models.document_version import DocumentVersion
from ..schemas.document import DocumentUploadResponse, DocumentDetailResponse
from ..services.storage_service import upload_file
from ..pipeline.ingestion import ingest_document

logger = logging.getLogger(__name__)


async def upload_document(
    file: UploadFile,
    tenant_id: UUID,
    user_id: UUID,
    db: AsyncSession,
) -> DocumentUploadResponse:
    """Upload a document to S3, create DB records, and schedule async ingestion."""
    file_bytes = await file.read()

    # Compute file hash for deduplication
    file_hash = hashlib.sha256(file_bytes).hexdigest()

    doc_id = uuid.uuid4()
    version_id = uuid.uuid4()

    s3_key = f"{tenant_id}/{doc_id}/{version_id}/{file.filename}"

    # Upload to S3
    await upload_file(file_bytes, s3_key, file.content_type or "application/octet-stream")

    # Create Document record
    doc = Document(
        id=doc_id,
        tenant_id=tenant_id,
        created_by=user_id,
        title=file.filename or "Unknown",
        status="pending",
    )
    db.add(doc)

    # Create DocumentVersion record
    version = DocumentVersion(
        id=version_id,
        document_id=doc_id,
        s3_path=s3_key,
        version_number=1,
        file_hash=file_hash,
        file_size_bytes=len(file_bytes),
        original_filename=file.filename,
        uploaded_by=user_id,
    )
    db.add(version)

    await db.flush()  # get doc/version into DB before committing

    # Set current_version_id on document
    doc.current_version_id = version_id
    await db.commit()
    await db.refresh(doc)

    # Enqueue the ingestion task
    await ingest_document(
        document_id=doc_id,
        version_id=version_id,
        s3_path=s3_key,
        tenant_id=tenant_id,
    )

    return DocumentUploadResponse(
        document_id=doc_id,
        version_id=version_id,
        title=doc.title,
        status=doc.status,
        created_at=doc.created_at,
    )


async def get_document(
    document_id: UUID,
    tenant_id: UUID,
    db: AsyncSession,
) -> DocumentDetailResponse:
    """Retrieve a document with its versions and extracted metadata."""
    stmt = (
        select(Document)
        .where(Document.id == document_id, Document.tenant_id == tenant_id)
        .options(
            selectinload(Document.versions),
            selectinload(Document.metadata_items),
        )
    )
    res = await db.execute(stmt)
    doc = res.scalar_one_or_none()

    if not doc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found or access denied",
        )

    versions = [
        {
            "id": str(v.id),
            "version": v.version_number,
            "s3_path": v.s3_path,
            "created_at": v.created_at.isoformat(),
        }
        for v in doc.versions
    ]
    curr_version = next(
        (v for v in versions if str(v["id"]) == str(doc.current_version_id)),
        versions[-1] if versions else None,
    )

    # Format metadata as [{key, value, source, confidence_score}]
    meta = [
        {
            "key": m.key,
            "value": m.value,
            "source": m.source,
            "confidence_score": m.confidence_score,
        }
        for m in doc.metadata_items
    ]

    return DocumentDetailResponse(
        document_id=doc.id,
        title=doc.title,
        doc_type=doc.doc_type,
        status=doc.status,
        created_at=doc.created_at,
        current_version=curr_version,
        metadata=meta,
        versions=versions,
    )