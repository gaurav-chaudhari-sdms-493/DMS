"""T51/T52/T54/T55 — the Human Verification Workbench's fact lane.

Mirrors entity_graph_service.py's confirm_edge/bulk_confirm_edges (T56/
T57) exactly, so facts and entity edges go through the same shape of
promotion. 'machine' facts are never promoted further — permanent, same
as tier1/2 edges. Only 'in_review' facts can reach 'verified', and only
through a real actor event (T55's hard rule; enforced the same way T08
enforces it everywhere else — no actor_id, no write).

Do not build a gate that blocks indexing (Section 3.5) — nothing here
touches search or chunk indexing, which already happened at ingest
regardless of a fact's verification status.
"""
import uuid as uuid_module
from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import UUID

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.audit_log import AuditLog
from app.models.document import Document
from app.models.fact import Fact
from app.services.audit_service import log_action


async def claim_fact(db: AsyncSession, tenant_id: UUID, fact_id: UUID, actor_id: UUID) -> Fact:
    """T52 — a courtesy lock, not a hard gate: confirm_fact() doesn't
    require a claim, this just stops two operators working the same item
    without knowing it."""
    fact = await db.get(Fact, fact_id)
    if not fact or fact.tenant_id != tenant_id:
        raise HTTPException(status_code=404, detail="Fact not found")

    if fact.claimed_by_actor_id and fact.claimed_by_actor_id != actor_id:
        raise HTTPException(status_code=409, detail="Fact is already claimed by another operator")

    fact.claimed_by_actor_id = actor_id
    fact.claimed_at = datetime.utcnow()
    await db.flush()
    return fact


async def release_fact(db: AsyncSession, tenant_id: UUID, fact_id: UUID, actor_id: UUID) -> Fact:
    fact = await db.get(Fact, fact_id)
    if not fact or fact.tenant_id != tenant_id:
        raise HTTPException(status_code=404, detail="Fact not found")

    if fact.claimed_by_actor_id and fact.claimed_by_actor_id != actor_id:
        raise HTTPException(status_code=409, detail="Only the operator who claimed this fact can release it")

    fact.claimed_by_actor_id = None
    fact.claimed_at = None
    await db.flush()
    return fact


async def confirm_fact(db: AsyncSession, tenant_id: UUID, fact_id: UUID, actor_id: UUID) -> Fact:
    """T51 — the single-fact human confirmation action: in_review -> verified.

    'machine' facts are never promoted here, same reasoning as T56's
    edges: a value the confidence bands already auto-committed keeps that
    label for good, even after a person has looked at it.
    """
    if actor_id is None:
        raise ValueError("confirmation requires an actor")  # same rule as T08

    fact = await db.get(Fact, fact_id)
    if not fact or fact.tenant_id != tenant_id:
        raise HTTPException(status_code=404, detail="Fact not found")

    if fact.status == "verified":
        raise HTTPException(status_code=409, detail="Fact is already verified")
    if fact.status != "in_review":
        raise HTTPException(
            status_code=409,
            detail=f"'{fact.status}' facts do not go through confirmation — auto-committed values stay permanently labelled",
        )

    fact.status = "verified"
    fact.verified_by_actor_id = actor_id
    fact.verified_at = datetime.utcnow()
    fact.claimed_by_actor_id = None
    fact.claimed_at = None
    await db.flush()

    await log_action(
        db, actor_id, tenant_id, "fact.confirm",
        resource_type="fact", resource_id=fact.id,
        details={"field_name": fact.field_name, "is_handwritten": fact.is_handwritten},
    )

    return fact


async def mark_fact_handwritten(db: AsyncSession, tenant_id: UUID, fact_id: UUID, actor_id: UUID) -> Fact:
    """T30 — operator capture: a human notices a value is handwritten even
    though extraction didn't flag it (or the field predates T30's prompt
    change). Demotes 'machine' to 'in_review' — a fact now known to be
    handwritten cannot stay in an auto-committed, never-reviewed state,
    which is the whole point of "never verified without a human."
    'verified' stays 'verified': a person already looked at it and
    confirmed it; this corrects the record, it doesn't reopen a decision
    a human already made.
    """
    if actor_id is None:
        raise ValueError("marking a fact handwritten requires an actor")

    fact = await db.get(Fact, fact_id)
    if not fact or fact.tenant_id != tenant_id:
        raise HTTPException(status_code=404, detail="Fact not found")

    previous_status = fact.status
    fact.is_handwritten = True
    if fact.status == "machine":
        fact.status = "in_review"
    await db.flush()

    await log_action(
        db, actor_id, tenant_id, "fact.mark_handwritten",
        resource_type="fact", resource_id=fact.id,
        details={"field_name": fact.field_name, "previous_status": previous_status, "new_status": fact.status},
    )

    return fact


async def bulk_confirm_facts(
    db: AsyncSession,
    tenant_id: UUID,
    corpus_folder_id: UUID,
    threshold: float,
    actor_id: UUID,
    policy_version: str,
) -> dict:
    """T54 — batch accept every in_review fact above a chosen confidence for
    one corpus, in one action. Record the user, the score, the collection
    and the rule version — on the log and on every fact it touched.

    T55 hard rule: a handwritten fact is never included here, confidence
    notwithstanding — only confirm_fact() (a real person looking at that
    one fact) can verify one. T59: bulk acceptance is disabled on an
    uncalibrated corpus, same gate T57 already applies to entity edges —
    an uncalibrated confidence score "implies calibrated confidence and
    carries none."
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
        select(Fact)
        .join(Document, Fact.document_id == Document.id)
        .where(
            Fact.tenant_id == tenant_id,
            Fact.status == "in_review",
            Fact.confidence.is_not(None),
            Fact.confidence >= threshold,
            Fact.is_handwritten == False,  # noqa: E712 — T55 hard rule
            Document.folder_id == corpus_folder_id,
        )
    )
    res = await db.execute(stmt)
    facts = list(res.scalars().all())

    batch_id = uuid_module.uuid4()
    now = datetime.utcnow()
    for fact in facts:
        fact.status = "verified"
        fact.verified_by_actor_id = actor_id
        fact.verified_at = now
        fact.verified_threshold = threshold
        fact.verified_corpus_folder_id = corpus_folder_id
        fact.verified_via_policy_version = policy_version
        fact.verified_batch_id = batch_id
        fact.claimed_by_actor_id = None
        fact.claimed_at = None

    await db.flush()

    await log_action(
        db, actor_id, tenant_id, "fact.bulk_confirm",
        resource_type="folder", resource_id=corpus_folder_id,
        details={
            "batch_id": str(batch_id),
            "threshold": threshold,
            "policy_version": policy_version,
            "confirmed_count": len(facts),
            "fact_ids": [str(f.id) for f in facts],
        },
    )

    return {"batch_id": batch_id, "confirmed_count": len(facts), "fact_ids": [f.id for f in facts]}


async def get_adjudication_queue(
    db: AsyncSession, tenant_id: UUID, category: str = "low_confidence", limit: int = 50, offset: int = 0,
) -> dict:
    """T52 — adjudication queue. 'low_confidence' is any in_review fact.
    'handwritten' filters on is_handwritten, which T30's VLM extraction
    prompt now sets per field (and mark_fact_handwritten lets an operator
    correct after the fact). 'marginalia' filters on the field_name
    sentinel T30's extraction path writes handwritten notes under
    ("_marginalia") — same Fact+FactRegion shape as every other queue
    item, not a separate data source. 'join_mismatch' still isn't backed
    by anything (it would come from Handler 1/T26's spread-join, which
    isn't wired into extraction — T22's own documented gap, blocked on
    A1) — requesting it raises rather than silently returning an
    always-empty queue that looks like "nothing to review" instead of
    "not built yet".
    """
    valid_categories = {"low_confidence", "handwritten", "marginalia"}
    not_yet_available = {"join_mismatch"}
    if category in not_yet_available:
        raise HTTPException(
            status_code=501,
            detail=f"'{category}' queue category has no data source yet — spread-join wiring (T26 handler integration) isn't built",
        )
    if category not in valid_categories:
        raise HTTPException(status_code=400, detail=f"Unknown category '{category}'. Valid: {sorted(valid_categories | not_yet_available)}")

    conditions = [Fact.tenant_id == tenant_id, Fact.status == "in_review"]
    if category == "handwritten":
        conditions.append(Fact.is_handwritten == True)  # noqa: E712
        conditions.append(Fact.field_name != "_marginalia")
    elif category == "marginalia":
        conditions.append(Fact.field_name == "_marginalia")

    from sqlalchemy import func
    count_res = await db.execute(select(func.count(Fact.id)).where(*conditions))
    total = count_res.scalar() or 0

    res = await db.execute(
        select(Fact).where(*conditions).order_by(Fact.confidence.asc().nulls_first()).limit(limit).offset(offset)
    )
    facts = list(res.scalars().all())

    return {
        "category": category,
        "total": total,
        "facts": [
            {
                "fact_id": str(f.id),
                "document_id": str(f.document_id),
                "field_name": f.field_name,
                "value": f.value,
                "confidence": f.confidence,
                "is_handwritten": f.is_handwritten,
                "claimed_by_actor_id": str(f.claimed_by_actor_id) if f.claimed_by_actor_id else None,
            }
            for f in facts
        ],
    }


async def bulk_edit_facts(
    db: AsyncSession, tenant_id: UUID, edits: List[Dict[str, Any]], actor_id: UUID, dry_run: bool = False,
) -> dict:
    """T80 — correct many facts' values in one action: the bulk version
    of the checking screen's single-fact [C] correct action (Section 5),
    not a bulk version of T51's confirm. An edit NEVER sets 'verified' —
    it always lands at 'in_review', whatever the fact's status was
    before, clearing any prior verification (confirming a fact attests to
    a specific value; a changed value hasn't been looked at by anyone).
    That's how "cannot promote machine values to verified" (Section 10)
    holds by construction, not by a separate check.

    dry_run=True runs every validation and computes the same before/after
    preview without writing anything — "show a preview before applying"
    is the same code path as applying, not a second implementation that
    could drift from it.

    `edits` is an explicit list of {"fact_id": UUID, "new_value": Any} —
    exactly which facts change and what they change to is decided by the
    caller (the workbench UI, T54), not a find-and-replace pattern
    matched server-side.
    """
    if actor_id is None:
        raise ValueError("bulk edit requires an actor")
    if not edits:
        raise ValueError("no edits provided")

    fact_ids = [e["fact_id"] for e in edits]
    res = await db.execute(select(Fact).where(Fact.tenant_id == tenant_id, Fact.id.in_(fact_ids)))
    facts_by_id = {f.id: f for f in res.scalars().all()}

    batch_id = uuid_module.uuid4()
    rows = []
    changed_count = 0

    for edit in edits:
        fact_id = edit["fact_id"]
        new_value = edit["new_value"]
        fact = facts_by_id.get(fact_id)
        if not fact:
            rows.append({"fact_id": str(fact_id), "error": "not found"})
            continue

        previous_value = fact.value
        previous_status = fact.status
        if previous_value == new_value:
            rows.append({
                "fact_id": str(fact_id), "field_name": fact.field_name,
                "previous_value": previous_value, "new_value": new_value,
                "changed": False,
            })
            continue

        changed_count += 1
        rows.append({
            "fact_id": str(fact_id), "field_name": fact.field_name,
            "previous_value": previous_value, "new_value": new_value,
            "previous_status": previous_status, "new_status": "in_review",
            "changed": True,
        })

        if not dry_run:
            fact.value = new_value
            fact.status = "in_review"
            fact.verified_by_actor_id = None
            fact.verified_at = None
            fact.verified_threshold = None
            fact.verified_corpus_folder_id = None
            fact.verified_via_policy_version = None
            fact.verified_batch_id = None
            fact.claimed_by_actor_id = None
            fact.claimed_at = None

            await log_action(
                db, actor_id, tenant_id, "fact.bulk_edit",
                resource_type="fact", resource_id=fact.id,
                details={
                    "batch_id": str(batch_id),
                    "field_name": fact.field_name,
                    "previous_value": previous_value,
                    "new_value": new_value,
                    "previous_status": previous_status,
                },
            )

    if not dry_run and changed_count:
        await db.flush()

    return {
        "batch_id": str(batch_id) if not dry_run and changed_count else None,
        "dry_run": dry_run,
        "total": len(edits),
        "changed_count": changed_count,
        "rows": rows,
    }


async def revert_bulk_edit_batch(db: AsyncSession, tenant_id: UUID, batch_id: UUID, actor_id: UUID) -> dict:
    """T80 — bounded undo: restore every fact one bulk-edit batch touched
    to its pre-edit value and status. The audit log (append-only, T63) is
    the source of truth for what to restore — no separate value-history
    table, same "history lives in the audit log, not on the live row"
    design T58's edge revert already established.

    Bounded on purpose: this restores content and review-state (value,
    status), not the full prior verification provenance (who verified
    it, when, under what threshold) — that stays in the audit log to
    consult, it isn't auto-resurrected. One level of undo, not a stack —
    reverting a batch twice is a no-op the second time (nothing left at
    'in_review' from this batch to distinguish from unrelated edits).
    """
    if actor_id is None:
        raise ValueError("reverting a bulk edit requires an actor")

    stmt = select(AuditLog).where(
        AuditLog.actor_tenant_id == tenant_id,
        AuditLog.action == "fact.bulk_edit",
        AuditLog.details["batch_id"].astext == str(batch_id),
    )
    res = await db.execute(stmt)
    log_entries = list(res.scalars().all())
    if not log_entries:
        raise HTTPException(status_code=404, detail="No bulk-edit batch found with this id")

    fact_ids = [entry.resource_id for entry in log_entries]
    facts_res = await db.execute(select(Fact).where(Fact.tenant_id == tenant_id, Fact.id.in_(fact_ids)))
    facts_by_id = {f.id: f for f in facts_res.scalars().all()}

    reverted = []
    for entry in log_entries:
        fact = facts_by_id.get(entry.resource_id)
        if not fact:
            continue
        fact.value = entry.details["previous_value"]
        fact.status = entry.details["previous_status"]
        reverted.append(str(fact.id))

    await db.flush()

    await log_action(
        db, actor_id, tenant_id, "fact.bulk_edit_revert",
        resource_type="fact_batch", resource_id=batch_id,
        details={"batch_id": str(batch_id), "reverted_count": len(reverted), "fact_ids": reverted},
    )

    return {"reverted_count": len(reverted), "fact_ids": reverted}
