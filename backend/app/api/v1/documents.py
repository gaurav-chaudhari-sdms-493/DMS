from typing import List, Optional
from fastapi import APIRouter, Depends, UploadFile, File, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from ...schemas.document import (
    DocumentUploadResponse,
    DocumentDetailResponse,
    BatchDocumentUploadResponse,
    DocumentListItem,
    DocumentUpdate,
    DriveStatsResponse,
)
from ...schemas.auth import TokenPayload
from ...deps import get_db, require_tenant_access
from ...services import document_service
import uuid

router = APIRouter()


@router.post('/', response_model=DocumentUploadResponse, status_code=201)
async def upload_document_api(
    file: UploadFile,
    folder_id: Optional[uuid.UUID] = Query(None),
    current_user: TokenPayload = Depends(require_tenant_access),
    db: AsyncSession = Depends(get_db),
):
    tenant_id = uuid.UUID(current_user.tenant_id)
    user_id = uuid.UUID(current_user.sub)
    return await document_service.upload_document(file, tenant_id, user_id, db, folder_id=folder_id)


@router.post('/bulk', response_model=BatchDocumentUploadResponse, status_code=201)
async def upload_documents_bulk_api(
    files: List[UploadFile] = File(...),
    folder_id: Optional[uuid.UUID] = Query(None),
    current_user: TokenPayload = Depends(require_tenant_access),
    db: AsyncSession = Depends(get_db),
):
    tenant_id = uuid.UUID(current_user.tenant_id)
    user_id = uuid.UUID(current_user.sub)
    return await document_service.upload_documents_bulk(files, tenant_id, user_id, db, folder_id=folder_id)


@router.get('/drive/stats', response_model=DriveStatsResponse)
async def get_drive_stats_api(
    current_user: TokenPayload = Depends(require_tenant_access),
    db: AsyncSession = Depends(get_db),
):
    tenant_id = uuid.UUID(current_user.tenant_id)
    return await document_service.get_drive_stats(db, tenant_id)


@router.get('', response_model=List[DocumentListItem])
async def list_documents_api(
    folder_id: Optional[uuid.UUID] = Query(None),
    include_all: bool = Query(False),
    is_starred: Optional[bool] = Query(None),
    is_trashed: bool = Query(False),
    current_user: TokenPayload = Depends(require_tenant_access),
    db: AsyncSession = Depends(get_db),
):
    tenant_id = uuid.UUID(current_user.tenant_id)
    return await document_service.list_documents(
        db=db,
        tenant_id=tenant_id,
        folder_id=folder_id,
        include_all=include_all,
        is_starred=is_starred,
        is_trashed=is_trashed,
    )


@router.get('/{document_id}', response_model=DocumentDetailResponse)
async def get_document_api(
    document_id: uuid.UUID,
    current_user: TokenPayload = Depends(require_tenant_access),
    db: AsyncSession = Depends(get_db),
):
    tenant_id = uuid.UUID(current_user.tenant_id)
    return await document_service.get_document(document_id, tenant_id, db)


@router.patch('/{document_id}', response_model=DocumentListItem)
async def update_document_api(
    document_id: uuid.UUID,
    doc_in: DocumentUpdate,
    current_user: TokenPayload = Depends(require_tenant_access),
    db: AsyncSession = Depends(get_db),
):
    tenant_id = uuid.UUID(current_user.tenant_id)
    return await document_service.update_document(db, document_id, tenant_id, doc_in)


@router.post('/{document_id}/star', response_model=DocumentListItem)
async def toggle_star_document_api(
    document_id: uuid.UUID,
    current_user: TokenPayload = Depends(require_tenant_access),
    db: AsyncSession = Depends(get_db),
):
    tenant_id = uuid.UUID(current_user.tenant_id)
    return await document_service.toggle_star_document(db, document_id, tenant_id)


@router.post('/{document_id}/trash', response_model=DocumentListItem)
async def toggle_trash_document_api(
    document_id: uuid.UUID,
    current_user: TokenPayload = Depends(require_tenant_access),
    db: AsyncSession = Depends(get_db),
):
    tenant_id = uuid.UUID(current_user.tenant_id)
    return await document_service.toggle_trash_document(db, document_id, tenant_id)


@router.post('/trash/cleanup')
async def cleanup_trashed_items_api(
    retention_days: int = 30,
    current_user: TokenPayload = Depends(require_tenant_access),
    db: AsyncSession = Depends(get_db),
):
    return await document_service.cleanup_expired_trashed_items(db, retention_days=retention_days)


@router.delete('/{document_id}', status_code=status.HTTP_204_NO_CONTENT)
async def delete_document_api(
    document_id: uuid.UUID,
    current_user: TokenPayload = Depends(require_tenant_access),
    db: AsyncSession = Depends(get_db),
):
    tenant_id = uuid.UUID(current_user.tenant_id)
    await document_service.delete_document_permanently(db, document_id, tenant_id)