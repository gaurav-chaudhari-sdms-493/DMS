from fastapi import APIRouter, Depends, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession
from app.schemas.document import DocumentUploadResponse, DocumentDetailResponse
from app.schemas.auth import TokenPayload
from app.deps import get_db, require_tenant_access
from app.services.document_service import upload_document, get_document
import uuid

router = APIRouter()

@router.post('/', response_model=DocumentUploadResponse, status_code=201)
async def upload_document_api(
    file: UploadFile,
    current_user: TokenPayload = Depends(require_tenant_access),
    db: AsyncSession = Depends(get_db),
):
    tenant_id = uuid.UUID(current_user.tenant_id)
    user_id = uuid.UUID(current_user.sub)
    return await upload_document(file, tenant_id, user_id, db)

@router.get('/{document_id}', response_model=DocumentDetailResponse)
async def get_document_api(
    document_id: uuid.UUID,
    current_user: TokenPayload = Depends(require_tenant_access),
    db: AsyncSession = Depends(get_db),
):
    tenant_id = uuid.UUID(current_user.tenant_id)
    return await get_document(document_id, tenant_id, db)