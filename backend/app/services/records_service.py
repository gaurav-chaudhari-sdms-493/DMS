from typing import Any, Dict, List, Optional
from uuid import UUID

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.record import Record
from app.models.record_amendment import RecordAmendment, VALID_LEGAL_STATUSES
from app.services.audit_service import log_action

DEFAULT_LEGAL_STATUS = "in force"


async def create_record(
    db: AsyncSession,
    tenant_id: UUID,
    subject_node_id: UUID,
    record_type: str,
    base_fields: Dict[str, Any],
    base_evidence_fact_id: Optional[UUID] = None,
    created_by_actor_id: Optional[UUID] = None,
    created_by_policy_version: Optional[str] = None,
) -> Record:
    """T60 — the base entry. Never edited in place after creation; every
    later change is a RecordAmendment on top of this."""
    if created_by_actor_id is None and created_by_policy_version is None:
        raise ValueError("a record must have a creating actor or policy version")

    record = Record(
        tenant_id=tenant_id,
        subject_node_id=subject_node_id,
        record_type=record_type,
        base_fields=base_fields,
        base_evidence_fact_id=base_evidence_fact_id,
        created_by_actor_id=created_by_actor_id,
        created_by_policy_version=created_by_policy_version,
    )
    db.add(record)
    await db.flush()

    if created_by_actor_id is not None:
        await log_action(
            db, created_by_actor_id, tenant_id, "record.create",
            resource_type="record", resource_id=record.id,
            details={"record_type": record_type, "fields": list(base_fields.keys())},
        )

    return record


async def add_amendment(
    db: AsyncSession,
    tenant_id: UUID,
    record_id: UUID,
    amendment_type: str,
    effective_date,
    field_changes: Dict[str, Any],
    evidence_fact_id: UUID,
    legal_status: Optional[str] = None,
    created_by_actor_id: Optional[UUID] = None,
    created_by_policy_version: Optional[str] = None,
) -> RecordAmendment:
    """T60 — append a change to the chain. Amendments are never edited or
    deleted, only added — the chain only grows.
    """
    if created_by_actor_id is None and created_by_policy_version is None:
        raise ValueError("an amendment must have a creating actor or policy version")
    if not evidence_fact_id:
        raise ValueError("an amendment must cite its source page (evidence_fact_id)")
    if not field_changes and legal_status is None:
        raise ValueError("an amendment must change at least one field or the legal status")
    if legal_status is not None and legal_status not in VALID_LEGAL_STATUSES:
        raise ValueError(f"invalid legal_status {legal_status!r}; must be one of {VALID_LEGAL_STATUSES}")

    record = await db.get(Record, record_id)
    if not record or record.tenant_id != tenant_id:
        raise HTTPException(status_code=404, detail="Record not found")

    amendment = RecordAmendment(
        tenant_id=tenant_id,
        record_id=record_id,
        amendment_type=amendment_type,
        effective_date=effective_date,
        field_changes=field_changes,
        legal_status=legal_status,
        evidence_fact_id=evidence_fact_id,
        created_by_actor_id=created_by_actor_id,
        created_by_policy_version=created_by_policy_version,
    )
    db.add(amendment)
    await db.flush()

    if created_by_actor_id is not None:
        await log_action(
            db, created_by_actor_id, tenant_id, "record.amend",
            resource_type="record", resource_id=record_id,
            details={
                "amendment_id": str(amendment.id),
                "amendment_type": amendment_type,
                "effective_date": str(effective_date),
                "fields_changed": list(field_changes.keys()),
                "legal_status": legal_status,
            },
        )

    return amendment


async def _get_record_and_amendments(db: AsyncSession, tenant_id: UUID, record_id: UUID):
    record = await db.get(Record, record_id)
    if not record or record.tenant_id != tenant_id:
        raise HTTPException(status_code=404, detail="Record not found")

    stmt = (
        select(RecordAmendment)
        .where(RecordAmendment.record_id == record_id, RecordAmendment.tenant_id == tenant_id)
        .order_by(RecordAmendment.effective_date.asc(), RecordAmendment.created_at.asc())
    )
    res = await db.execute(stmt)
    amendments = list(res.scalars().all())
    return record, amendments


async def get_original_state(db: AsyncSession, tenant_id: UUID, record_id: UUID) -> dict:
    """The record exactly as first entered — no amendments applied."""
    record, _ = await _get_record_and_amendments(db, tenant_id, record_id)
    return {
        "fields": dict(record.base_fields),
        "legal_status": DEFAULT_LEGAL_STATUS,
        "source": {"kind": "base", "evidence_fact_id": record.base_evidence_fact_id},
    }


async def get_current_state(db: AsyncSession, tenant_id: UUID, record_id: UUID) -> dict:
    """T60's core guarantee — always DERIVED by replaying base + every
    amendment in effective_date order. Never a stored, editable value:
    call this again and you re-derive the exact same answer from the
    same chain, deterministically.

    Also returns per-field provenance — which amendment (or the base
    entry) last set each field, and its evidence — answering "why does
    this record say this?" with a specific citation, not just a number.
    """
    record, amendments = await _get_record_and_amendments(db, tenant_id, record_id)

    fields = dict(record.base_fields)
    legal_status = DEFAULT_LEGAL_STATUS
    provenance = {
        field: {"kind": "base", "evidence_fact_id": record.base_evidence_fact_id}
        for field in record.base_fields
    }

    for amendment in amendments:
        for field, value in amendment.field_changes.items():
            fields[field] = value
            provenance[field] = {
                "kind": "amendment",
                "amendment_id": amendment.id,
                "amendment_type": amendment.amendment_type,
                "effective_date": amendment.effective_date,
                "evidence_fact_id": amendment.evidence_fact_id,
            }
        if amendment.legal_status is not None:
            legal_status = amendment.legal_status

    return {"fields": fields, "legal_status": legal_status, "field_provenance": provenance}


async def get_full_history(db: AsyncSession, tenant_id: UUID, record_id: UUID) -> dict:
    """Base entry plus every amendment, in order — the complete, readable
    chain, each entry citing its own source page."""
    record, amendments = await _get_record_and_amendments(db, tenant_id, record_id)

    return {
        "base": {
            "fields": dict(record.base_fields),
            "record_type": record.record_type,
            "evidence_fact_id": record.base_evidence_fact_id,
            "created_at": record.created_at,
        },
        "amendments": [
            {
                "id": a.id,
                "amendment_type": a.amendment_type,
                "effective_date": a.effective_date,
                "field_changes": a.field_changes,
                "legal_status": a.legal_status,
                "evidence_fact_id": a.evidence_fact_id,
            }
            for a in amendments
        ],
    }
