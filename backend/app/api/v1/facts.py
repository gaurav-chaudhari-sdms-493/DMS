import uuid
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from ...schemas.auth import TokenPayload
from ...deps import get_db, require_tenant_access, require_role
from ...services import fact_service, fact_verification_service

router = APIRouter(prefix="/facts", tags=["Facts"])


@router.get("/queue")
async def get_adjudication_queue_api(
    category: str = "low_confidence",
    limit: int = 50,
    offset: int = 0,
    current_user: TokenPayload = Depends(require_tenant_access),
    db: AsyncSession = Depends(get_db),
):
    tenant_id = uuid.UUID(current_user.tenant_id)
    return await fact_verification_service.get_adjudication_queue(db, tenant_id, category=category, limit=limit, offset=offset)


@router.post("/bulk-confirm")
async def bulk_confirm_facts_api(
    corpus_folder_id: uuid.UUID,
    threshold: float,
    policy_version: str,
    current_user: TokenPayload = Depends(require_role('records_officer', 'operator', 'it_admin')),
    db: AsyncSession = Depends(get_db),
):
    tenant_id = uuid.UUID(current_user.tenant_id)
    user_id = uuid.UUID(current_user.sub)
    result = await fact_verification_service.bulk_confirm_facts(
        db, tenant_id, corpus_folder_id, threshold, user_id, policy_version,
    )
    return {
        "batch_id": str(result["batch_id"]),
        "confirmed_count": result["confirmed_count"],
        "fact_ids": [str(fid) for fid in result["fact_ids"]],
    }


@router.get("/{fact_id}")
async def get_fact_api(
    fact_id: uuid.UUID,
    current_user: TokenPayload = Depends(require_tenant_access),
    db: AsyncSession = Depends(get_db),
):
    tenant_id = uuid.UUID(current_user.tenant_id)
    return await fact_service.get_fact_with_regions(db, fact_id, tenant_id)


@router.post("/{fact_id}/claim")
async def claim_fact_api(
    fact_id: uuid.UUID,
    current_user: TokenPayload = Depends(require_role('records_officer', 'operator', 'it_admin')),
    db: AsyncSession = Depends(get_db),
):
    tenant_id = uuid.UUID(current_user.tenant_id)
    user_id = uuid.UUID(current_user.sub)
    fact = await fact_verification_service.claim_fact(db, tenant_id, fact_id, user_id)
    return {"fact_id": str(fact.id), "claimed_by_actor_id": str(fact.claimed_by_actor_id)}


@router.post("/{fact_id}/release")
async def release_fact_api(
    fact_id: uuid.UUID,
    current_user: TokenPayload = Depends(require_role('records_officer', 'operator', 'it_admin')),
    db: AsyncSession = Depends(get_db),
):
    tenant_id = uuid.UUID(current_user.tenant_id)
    user_id = uuid.UUID(current_user.sub)
    fact = await fact_verification_service.release_fact(db, tenant_id, fact_id, user_id)
    return {"fact_id": str(fact.id), "claimed_by_actor_id": None}


@router.post("/{fact_id}/mark-handwritten")
async def mark_fact_handwritten_api(
    fact_id: uuid.UUID,
    current_user: TokenPayload = Depends(require_role('records_officer', 'operator', 'it_admin')),
    db: AsyncSession = Depends(get_db),
):
    tenant_id = uuid.UUID(current_user.tenant_id)
    user_id = uuid.UUID(current_user.sub)
    fact = await fact_verification_service.mark_fact_handwritten(db, tenant_id, fact_id, user_id)
    return {"fact_id": str(fact.id), "is_handwritten": fact.is_handwritten, "status": fact.status}


@router.post("/{fact_id}/confirm")
async def confirm_fact_api(
    fact_id: uuid.UUID,
    current_user: TokenPayload = Depends(require_role('records_officer', 'operator', 'it_admin')),
    db: AsyncSession = Depends(get_db),
):
    tenant_id = uuid.UUID(current_user.tenant_id)
    user_id = uuid.UUID(current_user.sub)
    fact = await fact_verification_service.confirm_fact(db, tenant_id, fact_id, user_id)
    return {"fact_id": str(fact.id), "status": fact.status, "verified_by_actor_id": str(fact.verified_by_actor_id)}
