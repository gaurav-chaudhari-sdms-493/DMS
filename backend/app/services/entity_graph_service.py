from datetime import datetime
from typing import Optional
from uuid import UUID

from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.entity_edge import EntityEdge
from app.services.audit_service import log_action

# Tier 1 (structural) and tier 2 (mention) auto-commit as machine — low-risk,
# mechanical facts ("this page contains this row", "this row names X").
# Tier 3 (identity) and tier 4 (legal) are escrowed: held until a human
# confirms them, tier 4 always regardless of confidence (Section 6).
AUTO_COMMIT_TIERS = {1, 2}
ESCROW_TIERS = {3, 4}


async def create_edge(
    db: AsyncSession,
    tenant_id: UUID,
    edge_type: str,
    tier: int,
    source_node_id: UUID,
    target_type: str,
    target_node_id: Optional[UUID] = None,
    target_fact_id: Optional[UUID] = None,
    confidence: Optional[float] = None,
    evidence_fact_id: Optional[UUID] = None,
    created_by_actor_id: Optional[UUID] = None,
    created_by_policy_version: Optional[str] = None,
) -> EntityEdge:
    """T56 — create an edge with the tier's auto-commit/escrow policy applied.

    Status is never accepted as an input: tier decides it. Tier 1/2 land as
    'machine' immediately. Tier 3/4 always land as 'held', no matter how
    high `confidence` is or whether a human is doing the creating — "tier 4
    legal links human-only at any confidence" means confirmation is always
    a separate, later step, not something creation can shortcut.
    """
    if tier not in AUTO_COMMIT_TIERS | ESCROW_TIERS:
        raise ValueError(f"invalid tier {tier}; must be 1, 2, 3, or 4")
    if target_type not in ("entity", "fact"):
        raise ValueError(f"invalid target_type {target_type!r}; must be 'entity' or 'fact'")
    if created_by_actor_id is None and created_by_policy_version is None:
        raise ValueError("an edge must have a creating actor or policy version")

    status = "machine" if tier in AUTO_COMMIT_TIERS else "held"

    edge = EntityEdge(
        tenant_id=tenant_id,
        edge_type=edge_type,
        tier=tier,
        source_node_id=source_node_id,
        target_type=target_type,
        target_node_id=target_node_id,
        target_fact_id=target_fact_id,
        confidence=confidence,
        status=status,
        created_by_actor_id=created_by_actor_id,
        created_by_policy_version=created_by_policy_version,
        evidence_fact_id=evidence_fact_id,
    )
    db.add(edge)
    await db.flush()

    if created_by_actor_id is not None:
        await log_action(
            db, created_by_actor_id, tenant_id, "entity_edge.create",
            resource_type="entity_edge", resource_id=edge.id,
            details={"edge_type": edge_type, "tier": tier, "status": status, "confidence": confidence},
        )

    return edge


async def confirm_edge(db: AsyncSession, tenant_id: UUID, edge_id: UUID, actor_id: UUID) -> EntityEdge:
    """T56 — the single-edge human confirmation action: held -> verified.

    Tier 1/2 ('machine') edges are never promoted — "a link the machine
    created keeps that label for good, even after a person has looked at
    it" (Section 6). Only tier 3/4 'held' edges can be confirmed here.
    """
    if actor_id is None:
        raise ValueError("confirmation requires an actor")  # same rule as T08

    edge = await db.get(EntityEdge, edge_id)
    if not edge or edge.tenant_id != tenant_id:
        raise HTTPException(status_code=404, detail="Edge not found")

    if edge.status == "verified":
        raise HTTPException(status_code=409, detail="Edge is already verified")
    if edge.status != "held":
        raise HTTPException(
            status_code=409,
            detail=f"Tier {edge.tier} ('{edge.status}') edges do not go through confirmation — machine-accepted links stay permanently labelled",
        )

    edge.status = "verified"
    edge.verified_by_actor_id = actor_id
    edge.verified_at = datetime.utcnow()
    await db.flush()

    await log_action(
        db, actor_id, tenant_id, "entity_edge.confirm",
        resource_type="entity_edge", resource_id=edge.id,
        details={"edge_type": edge.edge_type, "tier": edge.tier},
    )

    return edge
