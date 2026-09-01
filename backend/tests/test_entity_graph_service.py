import pytest
import uuid
from fastapi import HTTPException
from app.database import AsyncSessionLocal
from app.models.tenant import Tenant
from app.models.user import User
from app.models.folder import Folder
from app.models.document import Document
from app.models.document_version import DocumentVersion
from app.models.fact import Fact
from app.models.entity_node import EntityNode
from app.services.entity_graph_service import (
    create_node, create_edge, confirm_edge, revert_edge, bulk_confirm_edges, revert_bulk_batch,
)
from app.services.corpus_calibration_service import calibrate_corpus


async def _make_corpus(db):
    """Tenant, actor, a calibrated corpus folder, one document + fact in
    it — enough for an edge to be placed in a corpus via its
    evidence_fact_id -> document -> folder chain."""
    tenant_id = uuid.uuid4()
    actor_id = uuid.uuid4()
    tenant = Tenant(id=tenant_id, name=f"EntityGraph Tenant {uuid.uuid4().hex[:6]}")
    user = User(id=actor_id, tenant_id=tenant_id, email=f"eg_{uuid.uuid4().hex[:6]}@test.com", hashed_password="pw")
    folder = Folder(id=uuid.uuid4(), tenant_id=tenant_id, name="EntityGraph Corpus")
    db.add_all([tenant, user, folder])
    await db.flush()

    doc = Document(id=uuid.uuid4(), tenant_id=tenant_id, title="eg doc", status="indexed", folder_id=folder.id)
    version = DocumentVersion(
        id=uuid.uuid4(), tenant_id=tenant_id, document_id=doc.id, version_number=1, s3_path="x",
        file_hash="deadbeef", file_size_bytes=1, original_filename="eg.pdf",
    )
    db.add_all([doc, version])
    await db.flush()
    doc.current_version_id = version.id
    await db.flush()

    fact = Fact(
        id=uuid.uuid4(), tenant_id=tenant_id, document_id=doc.id, version_id=version.id,
        field_name="name", value={"v": "Test"}, confidence=0.9, status="machine",
    )
    db.add(fact)
    await db.flush()

    node = EntityNode(id=uuid.uuid4(), tenant_id=tenant_id, entity_type="person", label="Test Person", attributes={})
    db.add(node)
    await db.flush()

    await calibrate_corpus(db, tenant_id, folder.id, actor_id, sample_size=10, notes="entity graph test calibration")

    return tenant_id, actor_id, folder.id, node.id, fact.id


@pytest.mark.asyncio
async def test_create_node_requires_actor():
    async with AsyncSessionLocal() as db:
        try:
            with pytest.raises(ValueError):
                await create_node(db, uuid.uuid4(), "person", "Jane Doe", None)
        finally:
            await db.rollback()
            await db.close()


@pytest.mark.asyncio
async def test_create_node_requires_entity_type_and_label():
    async with AsyncSessionLocal() as db:
        try:
            tenant_id, actor_id, folder_id, node_id, fact_id = await _make_corpus(db)
            with pytest.raises(ValueError):
                await create_node(db, tenant_id, "", "Jane Doe", actor_id)
            with pytest.raises(ValueError):
                await create_node(db, tenant_id, "person", "  ", actor_id)
        finally:
            await db.rollback()
            await db.close()


@pytest.mark.asyncio
async def test_create_node_happy_path_logs_audit_event():
    async with AsyncSessionLocal() as db:
        try:
            tenant_id, actor_id, folder_id, node_id, fact_id = await _make_corpus(db)
            node = await create_node(db, tenant_id, "person", "Jane Doe", actor_id, attributes={"role": "clerk"})
            assert node.entity_type == "person"
            assert node.label == "Jane Doe"
            assert node.attributes == {"role": "clerk"}
            assert node.tenant_id == tenant_id
        finally:
            await db.rollback()
            await db.close()


@pytest.mark.asyncio
async def test_confirm_edge_rejects_machine_tier():
    async with AsyncSessionLocal() as db:
        try:
            tenant_id, actor_id, folder_id, node_id, fact_id = await _make_corpus(db)
            edge = await create_edge(
                db, tenant_id, "mentioned_in", tier=2, source_node_id=node_id,
                target_type="fact", target_fact_id=fact_id, confidence=0.99,
                evidence_fact_id=fact_id, created_by_actor_id=actor_id,
            )
            assert edge.status == "machine"
            with pytest.raises(HTTPException) as exc_info:
                await confirm_edge(db, tenant_id, edge.id, actor_id)
            assert exc_info.value.status_code == 409
        finally:
            await db.rollback()
            await db.close()


@pytest.mark.asyncio
async def test_confirm_edge_promotes_held_to_verified():
    async with AsyncSessionLocal() as db:
        try:
            tenant_id, actor_id, folder_id, node_id, fact_id = await _make_corpus(db)
            edge = await create_edge(
                db, tenant_id, "has_id", tier=3, source_node_id=node_id,
                target_type="fact", target_fact_id=fact_id, confidence=0.9,
                evidence_fact_id=fact_id, created_by_actor_id=actor_id,
            )
            assert edge.status == "held"
            confirmed = await confirm_edge(db, tenant_id, edge.id, actor_id)
            assert confirmed.status == "verified"
            assert confirmed.verified_by_actor_id == actor_id
            assert confirmed.verified_at is not None
        finally:
            await db.rollback()
            await db.close()


@pytest.mark.asyncio
async def test_revert_edge_rejects_machine_tier_and_undoes_verified():
    async with AsyncSessionLocal() as db:
        try:
            tenant_id, actor_id, folder_id, node_id, fact_id = await _make_corpus(db)
            machine_edge = await create_edge(
                db, tenant_id, "mentioned_in", tier=1, source_node_id=node_id,
                target_type="fact", target_fact_id=fact_id, confidence=0.99,
                evidence_fact_id=fact_id, created_by_actor_id=actor_id,
            )
            with pytest.raises(HTTPException) as exc_info:
                await revert_edge(db, tenant_id, machine_edge.id, actor_id)
            assert exc_info.value.status_code == 409

            held_edge = await create_edge(
                db, tenant_id, "has_id", tier=3, source_node_id=node_id,
                target_type="fact", target_fact_id=fact_id, confidence=0.9,
                evidence_fact_id=fact_id, created_by_actor_id=actor_id,
            )
            confirmed = await confirm_edge(db, tenant_id, held_edge.id, actor_id)
            assert confirmed.status == "verified"
            reverted = await revert_edge(db, tenant_id, held_edge.id, actor_id)
            assert reverted.status == "held"
            assert reverted.verified_by_actor_id is None
        finally:
            await db.rollback()
            await db.close()


@pytest.mark.asyncio
async def test_bulk_confirm_edges_requires_calibrated_corpus():
    async with AsyncSessionLocal() as db:
        try:
            tenant_id = uuid.uuid4()
            actor_id = uuid.uuid4()
            tenant = Tenant(id=tenant_id, name=f"Uncalibrated EG Tenant {uuid.uuid4().hex[:6]}")
            user = User(id=actor_id, tenant_id=tenant_id, email=f"uncal_eg_{uuid.uuid4().hex[:6]}@test.com", hashed_password="pw")
            folder = Folder(id=uuid.uuid4(), tenant_id=tenant_id, name="Uncalibrated EG Corpus")
            db.add_all([tenant, user, folder])
            await db.flush()

            with pytest.raises(HTTPException) as exc_info:
                await bulk_confirm_edges(db, tenant_id, folder.id, 0.8, actor_id, "policy-v1")
            assert exc_info.value.status_code == 409
        finally:
            await db.rollback()
            await db.close()


@pytest.mark.asyncio
async def test_bulk_confirm_edges_and_revert_batch_round_trip():
    async with AsyncSessionLocal() as db:
        try:
            tenant_id, actor_id, folder_id, node_id, fact_id = await _make_corpus(db)
            edge = await create_edge(
                db, tenant_id, "has_id", tier=3, source_node_id=node_id,
                target_type="fact", target_fact_id=fact_id, confidence=0.95,
                evidence_fact_id=fact_id, created_by_actor_id=actor_id,
            )
            result = await bulk_confirm_edges(db, tenant_id, folder_id, 0.8, actor_id, "policy-v1")
            assert edge.id in result["edge_ids"]
            await db.refresh(edge)
            assert edge.status == "verified"
            assert edge.verified_batch_id == result["batch_id"]

            revert_result = await revert_bulk_batch(db, tenant_id, result["batch_id"], actor_id)
            assert edge.id in revert_result["edge_ids"]
            await db.refresh(edge)
            assert edge.status == "held"
            assert edge.verified_batch_id is None
        finally:
            await db.rollback()
            await db.close()
