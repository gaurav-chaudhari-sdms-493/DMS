import uuid
from fastapi import APIRouter, Depends, Response
from sqlalchemy.ext.asyncio import AsyncSession

from ...deps import get_db, require_tenant_access, require_role
from ...schemas.auth import TokenPayload
from ...services.audit_service import verify_chain_integrity
from ...services import completeness_service, certificate_service

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


@router.get("/certificate/{document_id}")
async def get_section63_certificate_api(
    document_id: uuid.UUID,
    current_user: TokenPayload = Depends(require_role(
        "records_officer", "legal_counsel", "department_head", "it_admin", "auditor"
    )),
    db: AsyncSession = Depends(get_db),
):
    """T65 — Section 63 certificate: hash value, algorithm name, dual
    signature blocks. DRAFT TEMPLATE — see certificate_service docstring;
    not valid for evidentiary use until legal counsel review (A3)."""
    tenant_id = uuid.UUID(current_user.tenant_id)
    user_id = uuid.UUID(current_user.sub)
    content, filename, content_type = await certificate_service.generate_section63_certificate(
        db, tenant_id, user_id, document_id,
    )
    return Response(
        content=content,
        media_type=content_type,
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


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
