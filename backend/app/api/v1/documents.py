from fastapi import APIRouter, Depends, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession
from ...schemas.document import DocumentUploadResponse, DocumentDetailResponse
from ...schemas.auth import TokenPayload
from ...deps import get_db
from ...services.document_service import upload_document, get_document
import uuid

router = APIRouter()

@router.post('/', response_model=DocumentUploadResponse, status_code=201)
async def upload_document_api(
    file: UploadFile,
    db: AsyncSession = Depends(get_db),
):
    # Hardcoded for development. Replace with actual user and tenant IDs.
    tenant_id = uuid.UUID("00000000-0000-0000-0000-000000000000")
    user_id = uuid.UUID("00000000-0000-0000-0000-000000000000")
    return await upload_document(file, tenant_id, user_id, db)

@router.get('/{document_id}', response_model=DocumentDetailResponse)
async def get_document_api(
    document_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    # Hardcoded for development. Replace with actual tenant ID.
    tenant_id = uuid.UUID("00000000-0000-0000-0000-000000000000")
    return await get_document(document_id, tenant_id, db)