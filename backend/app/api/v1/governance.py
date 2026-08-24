import uuid
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from ...deps import get_db, require_tenant_access, require_role
from ...schemas.auth import TokenPayload
from ...services.audit_service import verify_chain_integrity
from ...services import completeness_service

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


@router.get("/completeness/{corpus_folder_id}")
async def get_corpus_completeness_api(
    corpus_folder_id: uuid.UUID,
    current_user: TokenPayload = Depends(require_tenant_access),
    db: AsyncSession = Depends(get_db),
):
    """T76 — completeness/reconciliation dashboard, gap-scored per corpus."""
    tenant_id = uuid.UUID(current_user.tenant_id)
    return await completeness_service.get_corpus_completeness(db, tenant_id, corpus_folder_id)


@router.get("/completeness/{corpus_folder_id}/drill")
async def get_completeness_drill_api(
    corpus_folder_id: uuid.UUID,
    category: str,
    current_user: TokenPayload = Depends(require_tenant_access),
    db: AsyncSession = Depends(get_db),
):
    """T76 — drill-through: the actual rows behind one dashboard number."""
    tenant_id = uuid.UUID(current_user.tenant_id)
    return await completeness_service.get_completeness_drill(db, tenant_id, corpus_folder_id, category)
