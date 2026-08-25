import pytest
import uuid
from datetime import date
from app.database import AsyncSessionLocal
from app.models.tenant import Tenant
from app.models.user import User
from app.models.entity_node import EntityNode
from app.models.document import Document
from app.models.document_version import DocumentVersion
from app.models.fact import Fact
from app.services.records_service import create_record, add_amendment, get_full_history


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
async def test_get_full_history_returns_base_and_amendments_in_order():
    """T60/T62 — history is the base entry plus every amendment, replayed
    in effective_date order, each amendment citing its own source page."""
    async with AsyncSessionLocal() as db:
        try:
            tenant_id, actor_id, node_id = await _make_tenant_and_node(db)

            doc = Document(id=uuid.uuid4(), tenant_id=tenant_id, title="7/12 extract", status="indexed")
            version = DocumentVersion(
                id=uuid.uuid4(), document_id=doc.id, version_number=1, s3_path="x",
                file_hash="deadbeef", file_size_bytes=1, original_filename="712.pdf",
            )
            db.add_all([doc, version])
            await db.flush()

            base_fact = Fact(
                id=uuid.uuid4(), tenant_id=tenant_id, document_id=doc.id, version_id=version.id,
                field_name="valuation", value={"v": 1000}, confidence=0.9, status="machine",
            )
            corrigendum_fact = Fact(
                id=uuid.uuid4(), tenant_id=tenant_id, document_id=doc.id, version_id=version.id,
                field_name="valuation", value={"v": 1000000}, confidence=0.95, status="machine",
            )
            db.add_all([base_fact, corrigendum_fact])
            await db.flush()

            record = await create_record(
                db, tenant_id, node_id, "7_12_extract", {"valuation": 1000},
                base_evidence_fact_id=base_fact.id, created_by_actor_id=actor_id,
            )
            await add_amendment(
                db, tenant_id, record.id, amendment_type="corrigendum",
                effective_date=date(2026, 1, 1), field_changes={"valuation": 1000000},
                evidence_fact_id=corrigendum_fact.id, created_by_actor_id=actor_id,
            )

            history = await get_full_history(db, tenant_id, record.id)
            assert history["base"]["fields"] == {"valuation": 1000}
            assert history["base"]["evidence_fact_id"] == base_fact.id
            assert len(history["amendments"]) == 1
            assert history["amendments"][0]["field_changes"] == {"valuation": 1000000}
            assert history["amendments"][0]["evidence_fact_id"] == corrigendum_fact.id
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
