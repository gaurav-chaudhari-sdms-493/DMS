import uuid
from fastapi import APIRouter, Depends, Response
from sqlalchemy.ext.asyncio import AsyncSession

from ...schemas.auth import TokenPayload
from ...deps import get_db, require_role
from ...services import export_service

router = APIRouter(prefix="/export", tags=["Export"])


@router.get("/entity/{node_id}")
async def export_entity_api(
    node_id: uuid.UUID,
    format: str = "json",
    mode: str = "general_export",
    current_user: TokenPayload = Depends(require_role('records_officer', 'operator', 'legal_counsel', 'it_admin', 'auditor')),
    db: AsyncSession = Depends(get_db),
):
    tenant_id = uuid.UUID(current_user.tenant_id)
    user_id = uuid.UUID(current_user.sub)
    content, filename, content_type = await export_service.generate_export(
        db, tenant_id, user_id, node_id, format, mode,
    )
    return Response(
        content=content,
        media_type=content_type,
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
