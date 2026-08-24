import hashlib
import uuid
import logging
from datetime import datetime
from typing import List, Optional
from fastapi import UploadFile, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, update, delete
from sqlalchemy.orm import selectinload
from uuid import UUID

from ..models.document import Document
from ..models.document_version import DocumentVersion
from ..models.folder import Folder
from ..schemas.document import (
    DocumentUploadResponse,
    DocumentDetailResponse,
    BatchDocumentUploadResponse,
    DocumentListItem,
    DocumentUpdate,
    DriveStatsResponse,
)
from ..services.storage_service import upload_file, generate_presigned_url, delete_file
from ..services.audit_service import log_action
from ..pipeline.ingestion import ingest_document

logger = logging.getLogger(__name__)


async def upload_document(
    file: UploadFile,
    tenant_id: UUID,
    user_id: UUID,
    db: AsyncSession,
    folder_id: Optional[UUID] = None,
    force: bool = False,
) -> DocumentUploadResponse:
    """Upload a document to MinIO S3, create DB records, and schedule async ingestion."""
    if folder_id:
        folder = await db.get(Folder, folder_id)
        if not folder or folder.tenant_id != tenant_id:
            raise HTTPException(status_code=404, detail="Target folder not found")

    from app.config import settings
    ext = (file.filename or "").rsplit(".", 1)[-1].lower()
    if ext not in settings.allowed_upload_extensions:
        raise HTTPException(status_code=400, detail=f"File type '.{ext}' is not supported")

    file_bytes = await file.read()
    max_bytes = settings.max_upload_size_mb * 1024 * 1024
    if len(file_bytes) > max_bytes:
        raise HTTPException(status_code=413, detail=f"File exceeds the {settings.max_upload_size_mb} MB limit")

    file_hash = hashlib.sha256(file_bytes).hexdigest()

    # T79: the hash was always stored but never compared — surface an exact
    # duplicate to the operator instead of silently re-processing it. Never
    # drop the file: `force=True` lets the operator upload it anyway.
    if not force:
        dup_stmt = (
            select(Document, DocumentVersion)
            .join(DocumentVersion, DocumentVersion.document_id == Document.id)
            .where(
                DocumentVersion.file_hash == file_hash,
                Document.tenant_id == tenant_id,
                Document.is_trashed == False,
            )
            .limit(1)
        )
        dup_res = await db.execute(dup_stmt)
        dup_row = dup_res.first()
        if dup_row:
            existing_doc, existing_version = dup_row
            raise HTTPException(
                status_code=409,
                detail={
                    "message": "An identical file already exists in your drive.",
                    "existing_document_id": str(existing_doc.id),
                    "existing_document_title": existing_doc.title,
                    "existing_uploaded_at": existing_version.created_at.isoformat(),
                },
            )

    doc_id = uuid.uuid4()
    version_id = uuid.uuid4()
    s3_key = f"{tenant_id}/{doc_id}/{version_id}/{file.filename}"

    # Upload file to MinIO S3
    await upload_file(file_bytes, s3_key, file.content_type or "application/octet-stream")

    doc = Document(
        id=doc_id,
        tenant_id=tenant_id,
        created_by=user_id,
        folder_id=folder_id,
        title=file.filename or "Unknown",
        status="pending",
    )
    db.add(doc)

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

    await db.flush()
    doc.current_version_id = version_id
    await db.commit()
    await db.refresh(doc)

    await log_action(db, user_id, tenant_id, "document.create", resource_type="document", resource_id=doc.id, details={"title": doc.title})

    # Schedule async ingestion
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
        folder_id=doc.folder_id,
    )


async def upload_documents_bulk(
    files: List[UploadFile],
    tenant_id: UUID,
    user_id: UUID,
    db: AsyncSession,
    folder_id: Optional[UUID] = None,
) -> BatchDocumentUploadResponse:
    """Upload multiple documents into a folder, create DB records, and schedule async ingestion."""
    uploaded_docs: List[DocumentUploadResponse] = []
    failures: List[dict] = []

    for file in files:
        try:
            doc_resp = await upload_document(file, tenant_id, user_id, db, folder_id=folder_id)
            uploaded_docs.append(doc_resp)
        except Exception as err:
            logger.error(f"Failed to upload document {file.filename}: {err}")
            failures.append({"filename": file.filename, "error": str(err)})

    return BatchDocumentUploadResponse(
        documents=uploaded_docs,
        total=len(files),
        succeeded=len(uploaded_docs),
        failed=len(failures),
        failures=failures,
    )


async def list_documents(
    db: AsyncSession,
    tenant_id: UUID,
    folder_id: Optional[UUID] = None,
    include_all: bool = False,
    is_starred: Optional[bool] = None,
    is_trashed: bool = False,
) -> List[DocumentListItem]:
    stmt = (
        select(Document)
        .where(Document.tenant_id == tenant_id, Document.is_trashed == is_trashed)
        .options(selectinload(Document.versions))
    )

    if is_starred is not None:
        stmt = stmt.where(Document.is_starred == is_starred)
    elif not include_all and folder_id is not None:
        stmt = stmt.where(Document.folder_id == folder_id)
    elif not include_all and folder_id is None and is_starred is None and not is_trashed:
        stmt = stmt.where(Document.folder_id.is_(None))

    stmt = stmt.order_by(Document.created_at.desc())
    res = await db.execute(stmt)
    docs = res.scalars().all()

    items = []
    for doc in docs:
        curr_v = next((v for v in doc.versions if v.id == doc.current_version_id), doc.versions[-1] if doc.versions else None)
        size = curr_v.file_size_bytes if curr_v else 0
        s3_path = curr_v.s3_path if curr_v else None
        url = await generate_presigned_url(s3_path) if s3_path else None

        items.append(
            DocumentListItem(
                id=doc.id,
                title=doc.title,
                doc_type=doc.doc_type,
                status=doc.status,
                created_at=doc.created_at,
                folder_id=doc.folder_id,
                is_starred=doc.is_starred,
                is_trashed=doc.is_trashed,
                trashed_at=doc.trashed_at,
                file_size_bytes=size,
                current_version_id=doc.current_version_id,
                s3_path=s3_path,
                download_url=url,
            )
        )
    return items


async def get_document(
    document_id: UUID,
    tenant_id: UUID,
    db: AsyncSession,
    actor_id: UUID,
) -> DocumentDetailResponse:
    """Retrieve a document with its versions, presigned download link, and metadata."""
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

    versions = []
    for v in doc.versions:
        url = await generate_presigned_url(v.s3_path) if v.s3_path else ""
        versions.append({
            "id": str(v.id),
            "version": v.version_number,
            "s3_path": v.s3_path,
            "file_size_bytes": v.file_size_bytes,
            "download_url": url,
            "created_at": v.created_at.isoformat(),
        })

    curr_version = next(
        (v for v in versions if str(v["id"]) == str(doc.current_version_id)),
        versions[-1] if versions else None,
    )

    meta = [
        {
            "key": m.key,
            "value": m.value,
            "source": m.source,
            "confidence_score": m.confidence_score,
        }
        for m in doc.metadata_items
    ]

    await log_action(db, actor_id, tenant_id, "document.view", resource_type="document", resource_id=doc.id)

    return DocumentDetailResponse(
        document_id=doc.id,
        title=doc.title,
        doc_type=doc.doc_type,
        status=doc.status,
        created_at=doc.created_at,
        folder_id=doc.folder_id,
        is_starred=doc.is_starred,
        is_trashed=doc.is_trashed,
        trashed_at=doc.trashed_at,
        current_version=curr_version,
        metadata=meta,
        versions=versions,
    )


async def update_document(
    db: AsyncSession,
    document_id: UUID,
    tenant_id: UUID,
    doc_in: DocumentUpdate,
    actor_id: UUID,
) -> DocumentListItem:
    stmt = select(Document).where(Document.id == document_id, Document.tenant_id == tenant_id).options(selectinload(Document.versions))
    res = await db.execute(stmt)
    doc = res.scalar_one_or_none()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")

    changes = {}
    if doc_in.folder_id is not None:
        folder = await db.get(Folder, doc_in.folder_id)
        if not folder or folder.tenant_id != tenant_id:
            raise HTTPException(status_code=404, detail="Target folder not found")
        doc.folder_id = doc_in.folder_id
        changes["folder_id"] = str(doc_in.folder_id)

    if doc_in.title is not None:
        doc.title = doc_in.title
        changes["title"] = doc_in.title

    await db.commit()
    await db.refresh(doc)

    await log_action(db, actor_id, tenant_id, "document.update", resource_type="document", resource_id=doc.id, details=changes)

    curr_v = next((v for v in doc.versions if v.id == doc.current_version_id), doc.versions[-1] if doc.versions else None)
    size = curr_v.file_size_bytes if curr_v else 0
    s3_path = curr_v.s3_path if curr_v else None
    url = await generate_presigned_url(s3_path) if s3_path else None

    return DocumentListItem(
        id=doc.id,
        title=doc.title,
        doc_type=doc.doc_type,
        status=doc.status,
        created_at=doc.created_at,
        folder_id=doc.folder_id,
        is_starred=doc.is_starred,
        is_trashed=doc.is_trashed,
        trashed_at=doc.trashed_at,
        file_size_bytes=size,
        current_version_id=doc.current_version_id,
        s3_path=s3_path,
        download_url=url,
    )


async def toggle_star_document(db: AsyncSession, document_id: UUID, tenant_id: UUID, actor_id: UUID) -> DocumentListItem:
    stmt = select(Document).where(Document.id == document_id, Document.tenant_id == tenant_id).options(selectinload(Document.versions))
    res = await db.execute(stmt)
    doc = res.scalar_one_or_none()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")

    doc.is_starred = not doc.is_starred
    await db.commit()
    await db.refresh(doc)

    await log_action(db, actor_id, tenant_id, "document.star_toggle", resource_type="document", resource_id=doc.id, details={"is_starred": doc.is_starred})

    curr_v = next((v for v in doc.versions if v.id == doc.current_version_id), doc.versions[-1] if doc.versions else None)
    size = curr_v.file_size_bytes if curr_v else 0
    s3_path = curr_v.s3_path if curr_v else None
    url = await generate_presigned_url(s3_path) if s3_path else None

    return DocumentListItem(
        id=doc.id,
        title=doc.title,
        doc_type=doc.doc_type,
        status=doc.status,
        created_at=doc.created_at,
        folder_id=doc.folder_id,
        is_starred=doc.is_starred,
        is_trashed=doc.is_trashed,
        trashed_at=doc.trashed_at,
        file_size_bytes=size,
        current_version_id=doc.current_version_id,
        s3_path=s3_path,
        download_url=url,
    )


async def toggle_trash_document(db: AsyncSession, document_id: UUID, tenant_id: UUID, actor_id: UUID) -> DocumentListItem:
    stmt = select(Document).where(Document.id == document_id, Document.tenant_id == tenant_id).options(selectinload(Document.versions))
    res = await db.execute(stmt)
    doc = res.scalar_one_or_none()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")

    doc.is_trashed = not doc.is_trashed
    doc.trashed_at = datetime.utcnow() if doc.is_trashed else None
    await db.commit()
    await db.refresh(doc)

    await log_action(db, actor_id, tenant_id, "document.trash_toggle", resource_type="document", resource_id=doc.id, details={"is_trashed": doc.is_trashed})

    curr_v = next((v for v in doc.versions if v.id == doc.current_version_id), doc.versions[-1] if doc.versions else None)
    size = curr_v.file_size_bytes if curr_v else 0
    s3_path = curr_v.s3_path if curr_v else None
    url = await generate_presigned_url(s3_path) if s3_path else None

    return DocumentListItem(
        id=doc.id,
        title=doc.title,
        doc_type=doc.doc_type,
        status=doc.status,
        created_at=doc.created_at,
        folder_id=doc.folder_id,
        is_starred=doc.is_starred,
        is_trashed=doc.is_trashed,
        trashed_at=doc.trashed_at,
        file_size_bytes=size,
        current_version_id=doc.current_version_id,
        s3_path=s3_path,
        download_url=url,
    )


async def delete_document_permanently(db: AsyncSession, document_id: UUID, tenant_id: UUID, actor_id: UUID) -> None:
    stmt = select(Document).where(Document.id == document_id, Document.tenant_id == tenant_id).options(selectinload(Document.versions))
    res = await db.execute(stmt)
    doc = res.scalar_one_or_none()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")

    doc_title = doc.title

    for v in doc.versions:
        if v.s3_path:
            try:
                await delete_file(v.s3_path)
            except Exception as e:
                logger.warning(f"Error deleting file from S3: {e}")

    # Clear current_version_id self-referential foreign key
    doc.current_version_id = None
    await db.flush()

    # Cascade delete dependent rows in database
    from app.models.chunk import Chunk
    from app.models.metadata_item import MetadataItem
    from app.models.document_version import DocumentVersion

    await db.execute(delete(Chunk).where(Chunk.document_id == document_id))
    await db.execute(delete(MetadataItem).where(MetadataItem.document_id == document_id))
    await db.execute(delete(DocumentVersion).where(DocumentVersion.document_id == document_id))

    await db.delete(doc)
    await db.commit()

    await log_action(db, actor_id, tenant_id, "document.delete", resource_type="document", resource_id=document_id, details={"title": doc_title})


async def get_drive_stats(db: AsyncSession, tenant_id: UUID) -> DriveStatsResponse:
    # Folders count
    f_res = await db.execute(select(func.count(Folder.id)).where(Folder.tenant_id == tenant_id, Folder.is_trashed == False))
    total_folders = f_res.scalar() or 0

    # Documents count
    d_res = await db.execute(select(func.count(Document.id)).where(Document.tenant_id == tenant_id, Document.is_trashed == False))
    total_files = d_res.scalar() or 0

    # Starred count
    s_f = await db.execute(select(func.count(Folder.id)).where(Folder.tenant_id == tenant_id, Folder.is_starred == True, Folder.is_trashed == False))
    s_d = await db.execute(select(func.count(Document.id)).where(Document.tenant_id == tenant_id, Document.is_starred == True, Document.is_trashed == False))
    total_starred = (s_f.scalar() or 0) + (s_d.scalar() or 0)

    # Trashed count
    t_f = await db.execute(select(func.count(Folder.id)).where(Folder.tenant_id == tenant_id, Folder.is_trashed == True))
    t_d = await db.execute(select(func.count(Document.id)).where(Document.tenant_id == tenant_id, Document.is_trashed == True))
    total_trashed = (t_f.scalar() or 0) + (t_d.scalar() or 0)

    # Total size in bytes
    v_res = await db.execute(
        select(func.sum(DocumentVersion.file_size_bytes))
        .join(Document, Document.current_version_id == DocumentVersion.id)
        .where(Document.tenant_id == tenant_id)
    )
    total_bytes = v_res.scalar() or 0

    return DriveStatsResponse(
        total_files=total_files,
        total_folders=total_folders,
        total_starred=total_starred,
        total_trashed=total_trashed,
        total_size_bytes=total_bytes,
        total_bytes=total_bytes
    )


async def cleanup_expired_trashed_items(db: AsyncSession, retention_days: int = 30) -> dict:
    from datetime import datetime, timedelta
    from app.models.folder import Folder
    from app.services.folder_service import delete_folder_permanently

    cutoff = datetime.utcnow() - timedelta(days=retention_days)

    # 1. Fetch expired trashed documents (trashed_at <= cutoff)
    doc_stmt = select(Document.id, Document.tenant_id).where(
        Document.is_trashed == True,
        Document.trashed_at.is_not(None),
        Document.trashed_at <= cutoff
    )
    doc_res = await db.execute(doc_stmt)
    expired_docs = doc_res.all()

    deleted_doc_count = 0
    for d_id, t_id in expired_docs:
        try:
            await delete_document_permanently(db, d_id, t_id)
            deleted_doc_count += 1
        except Exception as e:
            logger.warning(f"Error purging expired trashed document {d_id}: {e}")

    # 2. Fetch expired trashed folders (trashed_at <= cutoff)
    folder_stmt = select(Folder.id, Folder.tenant_id).where(
        Folder.is_trashed == True,
        Folder.trashed_at.is_not(None),
        Folder.trashed_at <= cutoff
    )
    folder_res = await db.execute(folder_stmt)
    expired_folders = folder_res.all()

    deleted_folder_count = 0
    for f_id, t_id in expired_folders:
        try:
            await delete_folder_permanently(db, f_id, t_id)
            deleted_folder_count += 1
        except Exception as e:
            logger.warning(f"Error purging expired trashed folder {f_id}: {e}")

    logger.info(f"Purged {deleted_doc_count} expired documents and {deleted_folder_count} expired folders older than {retention_days} days in Bin.")
    return {"deleted_documents": deleted_doc_count, "deleted_folders": deleted_folder_count}