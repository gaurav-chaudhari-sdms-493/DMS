"""Regression test for a real cross-tenant leak found and fixed 2026-09-02
(D-2 security review): get_entity_360_view()'s node/fact lookups had no
tenant_id filter, so any EntityEdge pointing at another tenant's
node/fact -- however it got created -- would have its real content
returned. Tested independently of the create_edge() write-side fix (this
test inserts the cross-tenant edge directly, not through create_edge()),
since a pre-existing bad row or any other future write path should still
be caught here as defense in depth, not rely on the write side alone."""
import uuid

import pytest

from app.database import AsyncSessionLocal
from app.models.tenant import Tenant
from app.models.user import User
from app.models.document import Document
from app.models.document_version import DocumentVersion
from app.models.fact import Fact
from app.models.entity_node import EntityNode
from app.models.entity_edge import EntityEdge
from app.services.entity_360_service import get_entity_360_view


async def _make_tenant_with_fact_and_node(db, secret_value):
    tenant_id = uuid.uuid4()
    actor_id = uuid.uuid4()
    tenant = Tenant(id=tenant_id, name=f"E360 Tenant {uuid.uuid4().hex[:6]}")
    user = User(id=actor_id, tenant_id=tenant_id, email=f"e360_{uuid.uuid4().hex[:6]}@test.com", hashed_password="pw")
    db.add_all([tenant, user])
    await db.flush()
    # actor_id returned below so callers have a real, FK-satisfying user
    # to attribute a directly-inserted edge to.

    doc = Document(id=uuid.uuid4(), tenant_id=tenant_id, title="e360 doc", status="indexed")
    version = DocumentVersion(
        id=uuid.uuid4(), document_id=doc.id, version_number=1, s3_path="x",
        file_hash=uuid.uuid4().hex, file_size_bytes=1, original_filename="e360.pdf",
    )
    db.add_all([doc, version])
    await db.flush()
    doc.current_version_id = version.id
    await db.flush()

    fact = Fact(
        id=uuid.uuid4(), tenant_id=tenant_id, document_id=doc.id, version_id=version.id,
        field_name="secret_field", value={"v": secret_value}, confidence=0.9, status="machine",
    )
    node = EntityNode(id=uuid.uuid4(), tenant_id=tenant_id, entity_type="person", label="E360 Person", attributes={})
    db.add_all([fact, node])
    await db.flush()

    return tenant_id, actor_id, node.id, fact.id


@pytest.mark.asyncio
async def test_entity_360_never_returns_another_tenants_fact_content():
    async with AsyncSessionLocal() as db:
        try:
            tenant_a, actor_a, node_a, _fact_a = await _make_tenant_with_fact_and_node(db, "tenant A's own value")
            tenant_b, _actor_b, _node_b, fact_b = await _make_tenant_with_fact_and_node(db, "TENANT B SECRET -- must never leak")

            # Directly insert a cross-tenant edge, bypassing create_edge()'s
            # own validation entirely -- this test must catch the leak even
            # if some other future write path (or pre-existing bad data)
            # produces a row create_edge() itself would now refuse.
            bad_edge = EntityEdge(
                id=uuid.uuid4(), tenant_id=tenant_a, edge_type="mentioned_in", tier=2,
                source_node_id=node_a, target_type="fact", target_fact_id=fact_b,
                status="machine", created_by_actor_id=actor_a,
            )
            db.add(bad_edge)
            await db.flush()

            view = await get_entity_360_view(db, tenant_a, node_a)

            linked_fact_ids = {lf["fact"]["fact_id"] for lf in view["linked_facts"]}
            assert str(fact_b) not in linked_fact_ids
            for lf in view["linked_facts"]:
                assert "TENANT B SECRET" not in str(lf["fact"].get("value", ""))
        finally:
            await db.rollback()
            await db.close()
