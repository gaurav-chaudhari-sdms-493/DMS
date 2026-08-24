import uuid
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from ...schemas.auth import TokenPayload
from ...deps import get_db, require_tenant_access
from ...services import entity_360_service

router = APIRouter(prefix="/entities", tags=["Entities"])


@router.get("/{node_id}/360")
async def get_entity_360_api(
    node_id: uuid.UUID,
    current_user: TokenPayload = Depends(require_tenant_access),
    db: AsyncSession = Depends(get_db),
):
    tenant_id = uuid.UUID(current_user.tenant_id)
    return await entity_360_service.get_entity_360_view(db, tenant_id, node_id)
