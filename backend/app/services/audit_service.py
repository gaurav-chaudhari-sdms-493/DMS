import hashlib
import json
import uuid
from datetime import datetime
from typing import Optional, Any

from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.audit_log import AuditLog

# T63 — genesis anchor for a tenant's very first chained event. Rows written
# before the hash chain existed have event_hash=NULL and are excluded from
# the chain entirely (see the model's docstring) rather than backfilled.
GENESIS_PREFIX = "veritasdocs-audit-chain-genesis:"


def _genesis_hash(tenant_id: uuid.UUID) -> str:
    return hashlib.sha256(f"{GENESIS_PREFIX}{tenant_id}".encode()).hexdigest()


def _canonical_payload(
    log_id: uuid.UUID, actor_id: uuid.UUID, tenant_id: uuid.UUID, action: str,
    resource_type: Optional[str], resource_id: Optional[uuid.UUID],
    ip_address: Optional[str], details: Optional[Any], created_at: datetime,
) -> str:
    return json.dumps({
        "id": str(log_id),
        "actor_id": str(actor_id),
        "tenant_id": str(tenant_id),
        "action": action,
        "resource_type": resource_type,
        "resource_id": str(resource_id) if resource_id else None,
        "ip_address": ip_address,
        "details": details,
        "created_at": created_at.isoformat(),
    }, sort_keys=True, default=str)


async def log_action(
    db: AsyncSession,
    actor_id: Optional[uuid.UUID],
    tenant_id: uuid.UUID,
    action: str,
    resource_type: Optional[str] = None,
    resource_id: Optional[uuid.UUID] = None,
    ip_address: Optional[str] = None,
    details: Optional[Any] = None,
    policy_version: Optional[str] = None,
) -> AuditLog:
    # T08: a chain full of empty user fields proves nothing — refuse any
    # change that has no actor attached, at the write layer, not just in
    # the UI. audit_dg_logs.actor_id is NOT NULL + FK'd to a real user row
    # at the DB level (stricter than the SQLAlchemy model declares) — a
    # scheduled/policy-driven action still needs a real actor_id (see
    # audit_service._resolve_policy_actor / T66's retention purge for how
    # one gets resolved for a non-human-initiated action). policy_version
    # is recorded alongside it as an annotation, not a substitute for it.
    if actor_id is None:
        raise ValueError(f"Refusing to write audit event '{action}': no actor_id provided")
    if policy_version is not None:
        details = {**(details or {}), "policy_version": policy_version}

    # T63: serialize chain appends per tenant so two concurrent log_action
    # calls can't both read the same tail and fork the chain. Released
    # automatically at transaction end.
    await db.execute(text("SELECT pg_advisory_xact_lock(hashtext(:t))"), {"t": str(tenant_id)})

    tail_res = await db.execute(
        select(AuditLog.event_hash)
        .where(AuditLog.actor_tenant_id == tenant_id, AuditLog.event_hash.is_not(None))
        .order_by(AuditLog.created_at.desc(), AuditLog.id.desc())
        .limit(1)
    )
    previous_hash = tail_res.scalar_one_or_none() or _genesis_hash(tenant_id)

    log_id = uuid.uuid4()
    created_at = datetime.utcnow()
    payload = _canonical_payload(log_id, actor_id, tenant_id, action, resource_type, resource_id, ip_address, details, created_at)
    event_hash = hashlib.sha256((previous_hash + payload).encode()).hexdigest()

    log = AuditLog(
        id=log_id,
        actor_tenant_id=tenant_id,
        actor_id=actor_id,
        action=action,
        resource_type=resource_type,
        resource_id=resource_id,
        ip_address=ip_address,
        details=details,
        created_at=created_at,
        previous_hash=previous_hash,
        event_hash=event_hash,
    )
    db.add(log)
    await db.flush()
    await db.refresh(log)
    return log


async def verify_chain_integrity(db: AsyncSession, tenant_id: uuid.UUID) -> dict:
    """T63 — the integrity checker: walk the chain in order, recompute each
    hash from its stored previous_hash + payload, and report the first row
    where the stored event_hash doesn't match. Only chained rows
    (event_hash IS NOT NULL) are walked — pre-chain rows are reported
    separately as unprotected, not treated as breaks.
    """
    unchained_res = await db.execute(
        select(AuditLog.id).where(AuditLog.actor_tenant_id == tenant_id, AuditLog.event_hash.is_(None))
    )
    unchained_count = len(unchained_res.scalars().all())

    res = await db.execute(
        select(AuditLog)
        .where(AuditLog.actor_tenant_id == tenant_id, AuditLog.event_hash.is_not(None))
        .order_by(AuditLog.created_at.asc(), AuditLog.id.asc())
    )
    rows = list(res.scalars().all())

    expected_previous = _genesis_hash(tenant_id)
    for i, row in enumerate(rows):
        if row.previous_hash != expected_previous:
            return {
                "valid": False, "checked_count": i, "unchained_count": unchained_count,
                "broken_at_id": row.id,
                "reason": "previous_hash does not match the expected chain position — a row may be missing or reordered",
            }

        payload = _canonical_payload(row.id, row.actor_id, row.actor_tenant_id, row.action, row.resource_type, row.resource_id, row.ip_address, row.details, row.created_at)
        recomputed = hashlib.sha256((row.previous_hash + payload).encode()).hexdigest()
        if recomputed != row.event_hash:
            return {
                "valid": False, "checked_count": i, "unchained_count": unchained_count,
                "broken_at_id": row.id,
                "reason": "event_hash does not match the recomputed hash — this row's content was altered after capture",
            }

        expected_previous = row.event_hash

    return {"valid": True, "checked_count": len(rows), "unchained_count": unchained_count, "broken_at_id": None, "reason": None}
