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
from ...deps import get_db, require_tenant_access, require_role
from ...services import document_service, classification_service
import uuid

router = APIRouter()


@router.post('/', response_model=DocumentUploadResponse, status_code=201)
async def upload_document_api(
    file: UploadFile,
    folder_id: Optional[uuid.UUID] = Query(None),
    force: bool = Query(False, description="Upload even if an identical file already exists"),
    current_user: TokenPayload = Depends(require_tenant_access),
    db: AsyncSession = Depends(get_db),
):
    tenant_id = uuid.UUID(current_user.tenant_id)
    user_id = uuid.UUID(current_user.sub)
    return await document_service.upload_document(file, tenant_id, user_id, db, folder_id=folder_id, force=force)


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


@router.get('/queue/unclassified')
async def list_unclassified_documents_api(
    limit: int = 50,
    offset: int = 0,
    current_user: TokenPayload = Depends(require_tenant_access),
    db: AsyncSession = Depends(get_db),
):
    tenant_id = uuid.UUID(current_user.tenant_id)
    return await classification_service.list_unclassified_documents(db, tenant_id, limit=limit, offset=offset)


@router.post('/{document_id}/classify')
async def classify_document_api(
    document_id: uuid.UUID,
    template_id: uuid.UUID,
    current_user: TokenPayload = Depends(require_role('records_officer', 'operator', 'it_admin')),
    db: AsyncSession = Depends(get_db),
):
    tenant_id = uuid.UUID(current_user.tenant_id)
    user_id = uuid.UUID(current_user.sub)
    doc = await classification_service.manually_classify_document(db, tenant_id, document_id, template_id, user_id)
    return {"document_id": str(doc.id), "classification_status": doc.classification_status, "matched_template_id": str(doc.matched_template_id)}


@router.post('/{document_id}/dismiss-classification')
async def dismiss_document_classification_api(
    document_id: uuid.UUID,
    current_user: TokenPayload = Depends(require_role('records_officer', 'operator', 'it_admin')),
    db: AsyncSession = Depends(get_db),
):
    tenant_id = uuid.UUID(current_user.tenant_id)
    user_id = uuid.UUID(current_user.sub)
    doc = await classification_service.dismiss_document_classification(db, tenant_id, document_id, user_id)
    return {"document_id": str(doc.id), "classification_status": doc.classification_status}


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
    user_id = uuid.UUID(current_user.sub)
    return await document_service.get_document(document_id, tenant_id, db, actor_id=user_id)


@router.patch('/{document_id}', response_model=DocumentListItem)
async def update_document_api(
    document_id: uuid.UUID,
    doc_in: DocumentUpdate,
    current_user: TokenPayload = Depends(require_tenant_access),
    db: AsyncSession = Depends(get_db),
):
    tenant_id = uuid.UUID(current_user.tenant_id)
    user_id = uuid.UUID(current_user.sub)
    return await document_service.update_document(db, document_id, tenant_id, doc_in, actor_id=user_id)


@router.post('/{document_id}/star', response_model=DocumentListItem)
async def toggle_star_document_api(
    document_id: uuid.UUID,
    current_user: TokenPayload = Depends(require_tenant_access),
    db: AsyncSession = Depends(get_db),
):
    tenant_id = uuid.UUID(current_user.tenant_id)
    user_id = uuid.UUID(current_user.sub)
    return await document_service.toggle_star_document(db, document_id, tenant_id, actor_id=user_id)


@router.post('/{document_id}/trash', response_model=DocumentListItem)
async def toggle_trash_document_api(
    document_id: uuid.UUID,
    current_user: TokenPayload = Depends(require_tenant_access),
    db: AsyncSession = Depends(get_db),
):
    tenant_id = uuid.UUID(current_user.tenant_id)
    user_id = uuid.UUID(current_user.sub)
    return await document_service.toggle_trash_document(db, document_id, tenant_id, actor_id=user_id)


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
    current_user: TokenPayload = Depends(require_role('records_officer', 'department_head', 'it_admin')),
    db: AsyncSession = Depends(get_db),
):
    tenant_id = uuid.UUID(current_user.tenant_id)
    user_id = uuid.UUID(current_user.sub)
    await document_service.delete_document_permanently(db, document_id, tenant_id, actor_id=user_id)