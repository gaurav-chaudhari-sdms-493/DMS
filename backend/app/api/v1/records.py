import uuid
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from ...schemas.auth import TokenPayload
from ...deps import get_db, require_tenant_access
from ...services import records_service
from ...models.record_amendment import VALID_LEGAL_STATUSES

router = APIRouter(prefix="/records", tags=["Records"])


@router.get("/by-status/{legal_status}")
async def list_records_by_status_api(
    legal_status: str,
    current_user: TokenPayload = Depends(require_tenant_access),
    db: AsyncSession = Depends(get_db),
):
    if legal_status not in VALID_LEGAL_STATUSES:
        raise HTTPException(status_code=422, detail=f"legal_status must be one of {VALID_LEGAL_STATUSES}")
    tenant_id = uuid.UUID(current_user.tenant_id)
    return await records_service.list_records_by_legal_status(db, tenant_id, legal_status)


@router.get("/status-summary")
async def get_legal_status_summary_api(
    current_user: TokenPayload = Depends(require_tenant_access),
    db: AsyncSession = Depends(get_db),
):
    tenant_id = uuid.UUID(current_user.tenant_id)
    return await records_service.get_legal_status_summary(db, tenant_id)
