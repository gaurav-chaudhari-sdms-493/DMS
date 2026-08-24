import uuid
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from ...schemas.auth import TokenPayload
from ...deps import get_db, require_tenant_access
from ...services import fact_service

router = APIRouter(prefix="/facts", tags=["Facts"])


@router.get("/{fact_id}")
async def get_fact_api(
    fact_id: uuid.UUID,
    current_user: TokenPayload = Depends(require_tenant_access),
    db: AsyncSession = Depends(get_db),
):
    tenant_id = uuid.UUID(current_user.tenant_id)
    return await fact_service.get_fact_with_regions(db, fact_id, tenant_id)
