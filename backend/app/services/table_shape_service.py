"""TS1 — shape-hash cache for table-fragment stitching decisions."""
from typing import Optional
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.table_shape_decision import TableShapeDecision


async def get_cached_shape_decision(db: AsyncSession, shape_hash: str) -> Optional[TableShapeDecision]:
    return await db.get(TableShapeDecision, shape_hash)


async def record_shape_decision(
    db: AsyncSession,
    shape_hash: str,
    relation: str,
    decided_by: str,
    confidence: Optional[float] = None,
    actor_id: Optional[UUID] = None,
) -> TableShapeDecision:
    existing = await db.get(TableShapeDecision, shape_hash)
    if existing:
        # A human decision (once TS4 wires review in) always supersedes an
        # earlier LLM guess for the same shape; an LLM verdict never
        # overwrites an existing human one.
        if existing.decided_by == "human" and decided_by != "human":
            return existing
        existing.relation = relation
        existing.confidence = confidence
        existing.decided_by = decided_by
        existing.decided_by_actor_id = actor_id
        await db.flush()
        return existing

    decision = TableShapeDecision(
        shape_hash=shape_hash, relation=relation, confidence=confidence,
        decided_by=decided_by, decided_by_actor_id=actor_id,
    )
    db.add(decision)
    await db.flush()
    return decision
