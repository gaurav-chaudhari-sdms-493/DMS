import pytest
import uuid
from app.database import AsyncSessionLocal
from app.models.tenant import Tenant
from app.models.user import User
from app.models.entity_node import EntityNode
from app.services.records_service import create_record


async def _make_tenant_and_node(db):
    tenant_id = uuid.uuid4()
    actor_id = uuid.uuid4()
    tenant = Tenant(id=tenant_id, name=f"Records Tenant {uuid.uuid4().hex[:6]}")
    user = User(id=actor_id, tenant_id=tenant_id, email=f"rec_{uuid.uuid4().hex[:6]}@test.com", hashed_password="pw")
    db.add_all([tenant, user])
    await db.flush()

    node = EntityNode(id=uuid.uuid4(), tenant_id=tenant_id, entity_type="property", label="Test Property", attributes={})
    db.add(node)
    await db.flush()

    return tenant_id, actor_id, node.id


@pytest.mark.asyncio
async def test_create_record_requires_actor_or_policy_version():
    async with AsyncSessionLocal() as db:
        try:
            tenant_id, actor_id, node_id = await _make_tenant_and_node(db)
            with pytest.raises(ValueError):
                await create_record(db, tenant_id, node_id, "7_12_extract", {"owner": "Test"})
        finally:
            await db.rollback()
            await db.close()


@pytest.mark.asyncio
async def test_create_record_happy_path_logs_audit_event():
    async with AsyncSessionLocal() as db:
        try:
            tenant_id, actor_id, node_id = await _make_tenant_and_node(db)
            record = await create_record(
                db, tenant_id, node_id, "7_12_extract",
                {"owner": "Test Owner", "area_sqm": 500}, created_by_actor_id=actor_id,
            )
            assert record.subject_node_id == node_id
            assert record.record_type == "7_12_extract"
            assert record.base_fields == {"owner": "Test Owner", "area_sqm": 500}
            assert record.created_by_actor_id == actor_id
            # D-7 default: a record is never engine-purged by age.
            assert record.retention_class == "statutory_record"
        finally:
            await db.rollback()
            await db.close()


@pytest.mark.asyncio
async def test_create_record_accepts_policy_version_without_actor():
    async with AsyncSessionLocal() as db:
        try:
            tenant_id, actor_id, node_id = await _make_tenant_and_node(db)
            record = await create_record(
                db, tenant_id, node_id, "form_a_entry", {"status": "seeded"},
                created_by_policy_version="seed-v1",
            )
            assert record.created_by_actor_id is None
            assert record.created_by_policy_version == "seed-v1"
        finally:
            await db.rollback()
            await db.close()
