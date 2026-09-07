"""T03 — the settings screen's backend. Zero coverage existed for
config_service.py before this file (only get_int/get_float were
exercised indirectly through whatever pipeline code calls them).

Uses a dedicated throwaway key (never a real seeded threshold like
chunk_size_tokens) for every test that mutates state, so a test run can
never leave a real engineering threshold changed -- sys_dg_config has no
tenant_id, it's genuinely global, and a leftover test mutation there
would affect every tenant's real behavior, not just a throwaway fixture."""
import uuid

import pytest
from fastapi import HTTPException
from sqlalchemy import delete

from app.database import AsyncSessionLocal
from app.models.sys_config import SysConfig
from app.models.tenant import Tenant
from app.models.user import User, UserRole
from app.services.auth_service import hash_password
from app.services import config_service

TEST_KEY = "test_config_service_dummy_threshold"


@pytest.fixture
async def dummy_config_row():
    async with AsyncSessionLocal() as db:
        db.add(SysConfig(key=TEST_KEY, value={"v": 0.5}, description="T03 test fixture — never read by real code"))
        await db.commit()
    yield TEST_KEY
    async with AsyncSessionLocal() as db:
        await db.execute(delete(SysConfig).where(SysConfig.key == TEST_KEY))
        await db.commit()
        # Clear the module-level read cache so a later test (or a real
        # get_config call in the same process) never sees this fixture's
        # value survive past its own cleanup.
        config_service._cache.pop(TEST_KEY, None)


@pytest.fixture
async def throwaway_actor():
    """No teardown deletes the User/Tenant here on purpose: set_config
    writes a real audit event per T08, and audit_dg_logs is append-only
    (a DB trigger rejects DELETE), which FK-blocks deleting the actor row
    it references. Same accepted tradeoff as this project's other tests
    that write real audit events -- a handful of harmless throwaway
    @test.com tenants/users persist in the dev DB rather than fighting
    the append-only guarantee the audit log is deliberately built on."""
    tenant_id = uuid.uuid4()
    user_id = uuid.uuid4()
    async with AsyncSessionLocal() as db:
        db.add(Tenant(id=tenant_id, name=f"T03 Test {uuid.uuid4().hex[:6]}"))
        await db.flush()
        db.add(User(
            id=user_id, tenant_id=tenant_id, email=f"t03_{uuid.uuid4().hex[:8]}@test.com",
            hashed_password=hash_password("x"), role=UserRole.it_admin,
        ))
        await db.commit()
    yield tenant_id, user_id


@pytest.mark.asyncio
async def test_list_all_config_includes_real_seeded_thresholds():
    """Read-only -- never mutates anything, safe against the real table."""
    async with AsyncSessionLocal() as db:
        rows = await config_service.list_all_config(db)
    keys = {r["key"] for r in rows}
    assert "chunk_size_tokens" in keys
    row = next(r for r in rows if r["key"] == "chunk_size_tokens")
    assert row["value"] == 512  # unwrapped from {"v": 512}, not the raw JSONB shape
    assert row["description"]


@pytest.mark.asyncio
async def test_set_config_updates_value(dummy_config_row, throwaway_actor):
    tenant_id, user_id = throwaway_actor
    async with AsyncSessionLocal() as db:
        result = await config_service.set_config(db, dummy_config_row, 0.75, user_id, tenant_id)
    assert result["value"] == 0.75

    async with AsyncSessionLocal() as db:
        rows = await config_service.list_all_config(db)
    row = next(r for r in rows if r["key"] == dummy_config_row)
    assert row["value"] == 0.75


@pytest.mark.asyncio
async def test_set_config_invalidates_the_read_cache_immediately(dummy_config_row, throwaway_actor):
    """An admin who just edited a threshold and watches the next document
    process through it shouldn't be looking at a stale cached value for
    up to _CACHE_TTL_SECONDS -- the whole point of invalidating on write."""
    tenant_id, user_id = throwaway_actor
    before = await config_service.get_float(dummy_config_row, 0.0)
    assert before == 0.5

    async with AsyncSessionLocal() as db:
        await config_service.set_config(db, dummy_config_row, 0.9, user_id, tenant_id)

    after = await config_service.get_float(dummy_config_row, 0.0)
    assert after == 0.9


@pytest.mark.asyncio
async def test_set_config_rejects_a_key_that_does_not_exist(throwaway_actor):
    """Deliberate: this endpoint edits an existing threshold, it never
    creates one -- a brand-new key needs a migration so it has a default
    for environments that haven't set it (see set_config's own docstring)."""
    tenant_id, user_id = throwaway_actor
    async with AsyncSessionLocal() as db:
        with pytest.raises(HTTPException) as exc_info:
            await config_service.set_config(db, "this_key_was_never_seeded", 1.0, user_id, tenant_id)
    assert exc_info.value.status_code == 404


@pytest.mark.asyncio
async def test_set_config_writes_a_real_audit_event(dummy_config_row, throwaway_actor):
    tenant_id, user_id = throwaway_actor
    async with AsyncSessionLocal() as db:
        await config_service.set_config(db, dummy_config_row, 0.33, user_id, tenant_id)

    async with AsyncSessionLocal() as db:
        from sqlalchemy import select
        from app.models.audit_log import AuditLog
        res = await db.execute(
            select(AuditLog).where(AuditLog.actor_id == user_id, AuditLog.action == "config.update")
        )
        entry = res.scalar_one()
        assert entry.details["key"] == dummy_config_row
        assert entry.details["old_value"] == 0.5
        assert entry.details["new_value"] == 0.33
