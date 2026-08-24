import uuid
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from ...deps import get_db, require_role
from ...schemas.auth import TokenPayload
from ...services.audit_service import verify_chain_integrity

router = APIRouter(prefix="/governance", tags=["Governance"])


@router.get("/audit-integrity")
async def check_audit_integrity_api(
    current_user: TokenPayload = Depends(require_role("auditor", "it_admin")),
    db: AsyncSession = Depends(get_db),
):
    """T50 + T63 — the integrity checker exposed as an endpoint, restricted
    to the two personas whose job it actually is to check it."""
    tenant_id = uuid.UUID(current_user.tenant_id)
    return await verify_chain_integrity(db, tenant_id)
