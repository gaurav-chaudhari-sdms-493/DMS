import uuid as uuid_module
from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import UUID

from fastapi import HTTPException
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.entity_edge import EntityEdge
from app.models.entity_node import EntityNode
from app.models.fact import Fact
from app.models.document import Document
from app.services.audit_service import log_action
from app.services.config_service import get_float

# Tier 1 (structural) and tier 2 (mention) auto-commit as machine — low-risk,
# mechanical facts ("this page contains this row", "this row names X").
# Tier 3 (identity) and tier 4 (legal) are escrowed: held until a human
# confirms them, tier 4 always regardless of confidence (Section 6).
AUTO_COMMIT_TIERS = {1, 2}
ESCROW_TIERS = {3, 4}


async def create_node(
    db: AsyncSession,
    tenant_id: UUID,
    entity_type: str,
    label: str,
    actor_id: UUID,
    attributes: Optional[Dict[str, Any]] = None,
) -> EntityNode:
    """T10 — register a real-world entity (person, property, office, ...)
    that edges and records can then be anchored to. Always a human/API
    action, not an automated pipeline step, so an actor is required
    unconditionally (same T08 rule as everything else that mutates and
    is audited)."""
    if actor_id is None:
        raise ValueError("creating a node requires an actor")
    if not entity_type or not entity_type.strip():
        raise ValueError("entity_type is required")
    if not label or not label.strip():
        raise ValueError("label is required")

    node = EntityNode(
        tenant_id=tenant_id,
        entity_type=entity_type.strip(),
        label=label.strip(),
        attributes=attributes or {},
    )
    db.add(node)
    await db.flush()

    await log_action(
        db, actor_id, tenant_id, "entity_node.create",
        resource_type="entity_node", resource_id=node.id,
        details={"entity_type": node.entity_type, "label": node.label},
    )

    return node


async def find_similar_nodes(
    db: AsyncSession,
    tenant_id: UUID,
    entity_type: str,
    label: str,
    exclude_node_id: Optional[UUID] = None,
    threshold: Optional[float] = None,
    limit: int = 5,
) -> List[Dict[str, Any]]:
    """Entity-graph accuracy — the biggest real risk here isn't the tier/
    escrow logic (that's deterministic), it's silent fragmentation: OCR/
    handwriting variance reads the same real-world entity as different
    text on different pages ("Shri Juni Masjid, Hirpur" vs "Shri Juni
    Masjid, Village. Hirpur, Taluka. Murtizapur" — both seen for the same
    masjid in one real document this session), and create_node() has no
    way to know that. Never auto-merges anything — same "surface for
    operator resolution, do not silently discard/decide" contract as the
    document fuzzy-duplicate leg (duplicate_service.find_fuzzy_duplicates,
    T79), just for entity labels instead of document content. Scoped to
    the same entity_type: a person and a property sharing trigrams is
    meaningless, never a duplicate candidate.

    pg_trgm's similarity() (not word_similarity(), which finds the best-
    matching substring of a long text against a short query — T72's
    search-leg use case) is the right function for two short, comparable
    labels compared head-to-head.
    """
    if threshold is None:
        threshold = await get_float("entity_dedup_similarity_threshold", 0.45)

    stmt = text("""
        SELECT id, entity_type, label, similarity(:label, label) AS score
        FROM entity_dg_nodes
        WHERE tenant_id = :tenant_id
          AND entity_type = :entity_type
          AND id != COALESCE(:exclude_node_id, '00000000-0000-0000-0000-000000000000'::uuid)
          AND similarity(:label, label) >= :threshold
        ORDER BY score DESC
        LIMIT :limit
    """)
    res = await db.execute(stmt, {
        "label": label.strip(),
        "tenant_id": str(tenant_id),
        "entity_type": entity_type.strip(),
        "exclude_node_id": str(exclude_node_id) if exclude_node_id else None,
        "threshold": threshold,
        "limit": limit,
    })
    return [
        {"id": str(row.id), "entity_type": row.entity_type, "label": row.label, "similarity": round(float(row.score), 4)}
        for row in res.fetchall()
    ]


async def search_nodes(
    db: AsyncSession,
    tenant_id: UUID,
    query: str,
    limit: int = 20,
) -> list[EntityNode]:
    """Name-based lookup so a user can find a node's ID from a person/
    property name instead of needing the raw UUID already in hand — the
    Entity 360 page previously only accepted a pasted ID with no way to
    discover one from the UI."""
    stmt = (
        select(EntityNode)
        .where(EntityNode.tenant_id == tenant_id, EntityNode.label.ilike(f"%{query.strip()}%"))
        .order_by(EntityNode.label)
        .limit(limit)
    )
    result = await db.execute(stmt)
    return list(result.scalars().all())


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


async def bulk_confirm_edges(
    db: AsyncSession,
    tenant_id: UUID,
    corpus_folder_id: UUID,
    threshold: float,
    actor_id: UUID,
    policy_version: str,
) -> dict:
    """T57 — bulk confirm is the same gate at scale: a person accepts every
    held edge above a chosen score for one collection, in one action.
    Record the user, the score, the collection and the rule version — on
    the log AND on every edge it touched (Section 6).

    "Corpus" is scoped to a folder, matching the existing container model
    (D-1). An edge is only reachable here through its evidence_fact_id ->
    document -> folder chain — an edge with no evidence (nullable per T10)
    can't be placed in any corpus and must go through confirm_edge()
    individually instead.

    Every confirmed edge gets a fresh verified_batch_id, the precise
    handle revert_bulk_batch() (T58) needs to undo exactly this run —
    policy_version is a reusable business label, not a unique run id.

    T59: bulk acceptance is disabled on a corpus until a human has
    calibrated it (corpus_calibration_service.calibrate_corpus) — a
    hardcoded/uncalibrated confidence score "implies calibrated
    confidence and carries none; any threshold built on it is
    meaningless" (scope gap, engineering standards).
    """
    if actor_id is None:
        raise ValueError("bulk confirmation requires an actor")
    if not policy_version:
        raise ValueError("bulk confirmation requires a policy/rule version")
    if threshold is None or not (0.0 <= threshold <= 1.0):
        raise ValueError("threshold must be between 0 and 1")

    from app.services.corpus_calibration_service import is_corpus_calibrated
    if not await is_corpus_calibrated(db, tenant_id, corpus_folder_id):
        raise HTTPException(
            status_code=409,
            detail="This corpus has not been calibrated — bulk acceptance is disabled until a human certifies "
                   "the confidence scores here are meaningful (corpus_calibration_service.calibrate_corpus)",
        )

    stmt = (
        select(EntityEdge)
        .join(Fact, EntityEdge.evidence_fact_id == Fact.id)
        .join(Document, Fact.document_id == Document.id)
        .where(
            EntityEdge.tenant_id == tenant_id,
            EntityEdge.status == "held",
            EntityEdge.confidence.is_not(None),
            EntityEdge.confidence >= threshold,
            Document.folder_id == corpus_folder_id,
        )
    )
    res = await db.execute(stmt)
    edges = list(res.scalars().all())

    batch_id = uuid_module.uuid4()
    now = datetime.utcnow()
    for edge in edges:
        edge.status = "verified"
        edge.verified_by_actor_id = actor_id
        edge.verified_at = now
        edge.verified_threshold = threshold
        edge.verified_corpus_folder_id = corpus_folder_id
        edge.verified_via_policy_version = policy_version
        edge.verified_batch_id = batch_id

    await db.flush()

    await log_action(
        db, actor_id, tenant_id, "entity_edge.bulk_confirm",
        resource_type="folder", resource_id=corpus_folder_id,
        details={
            "batch_id": str(batch_id),
            "threshold": threshold,
            "policy_version": policy_version,
            "confirmed_count": len(edges),
            "edge_ids": [str(e.id) for e in edges],
        },
    )

    return {"batch_id": batch_id, "confirmed_count": len(edges), "edge_ids": [e.id for e in edges]}


async def revert_edge(db: AsyncSession, tenant_id: UUID, edge_id: UUID, actor_id: UUID) -> EntityEdge:
    """T58 — link reversibility: undo one confirmation, verified -> held.

    "A link the machine created keeps that label for good, even after a
    person has looked at it" — machine (tier 1/2) edges can never be
    reverted because they were never a human decision to begin with.
    Reverting clears every verified_* field, whether the edge was
    confirmed individually or as part of a bulk batch — the *history* of
    who verified it and when lives in the append-only audit log, not on
    the live edge row.
    """
    if actor_id is None:
        raise ValueError("reverting a confirmation requires an actor")

    edge = await db.get(EntityEdge, edge_id)
    if not edge or edge.tenant_id != tenant_id:
        raise HTTPException(status_code=404, detail="Edge not found")

    if edge.status == "machine":
        raise HTTPException(
            status_code=409,
            detail="Machine-accepted links stay permanently labelled and cannot be reverted",
        )
    if edge.status == "held":
        raise HTTPException(status_code=409, detail="Edge is not verified — nothing to revert")

    previous_verifier = edge.verified_by_actor_id
    previous_batch_id = edge.verified_batch_id

    edge.status = "held"
    edge.verified_by_actor_id = None
    edge.verified_at = None
    edge.verified_threshold = None
    edge.verified_corpus_folder_id = None
    edge.verified_via_policy_version = None
    edge.verified_batch_id = None
    await db.flush()

    await log_action(
        db, actor_id, tenant_id, "entity_edge.revert",
        resource_type="entity_edge", resource_id=edge.id,
        details={
            "edge_type": edge.edge_type,
            "tier": edge.tier,
            "previously_verified_by": str(previous_verifier) if previous_verifier else None,
            "previous_batch_id": str(previous_batch_id) if previous_batch_id else None,
        },
    )

    return edge


async def revert_bulk_batch(db: AsyncSession, tenant_id: UUID, batch_id: UUID, actor_id: UUID) -> dict:
    """T58 — undo an entire bulk-confirm run in one action, by its exact
    batch_id. Clean cascade: reverts precisely the edges that batch
    touched, nothing from any other run, back to 'held'.
    """
    if actor_id is None:
        raise ValueError("reverting a bulk confirmation requires an actor")

    stmt = select(EntityEdge).where(
        EntityEdge.tenant_id == tenant_id,
        EntityEdge.verified_batch_id == batch_id,
        EntityEdge.status == "verified",
    )
    res = await db.execute(stmt)
    edges = list(res.scalars().all())

    for edge in edges:
        edge.status = "held"
        edge.verified_by_actor_id = None
        edge.verified_at = None
        edge.verified_threshold = None
        edge.verified_corpus_folder_id = None
        edge.verified_via_policy_version = None
        edge.verified_batch_id = None

    await db.flush()

    await log_action(
        db, actor_id, tenant_id, "entity_edge.bulk_revert",
        resource_type="entity_edge_batch", resource_id=batch_id,
        details={"reverted_count": len(edges), "edge_ids": [str(e.id) for e in edges]},
    )

    return {"reverted_count": len(edges), "edge_ids": [e.id for e in edges]}
