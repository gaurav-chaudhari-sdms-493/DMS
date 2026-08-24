from uuid import UUID

from fastapi import HTTPException
from sqlalchemy import select, or_, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.entity_node import EntityNode
from app.models.entity_edge import EntityEdge
from app.models.record import Record
from app.models.fact import Fact
from app.models.document import Document
from app.services.records_service import get_current_state, get_original_state


async def get_entity_360_view(db: AsyncSession, tenant_id: UUID, node_id: UUID) -> dict:
    """T62 — one entity, everything about it: its records (versions,
    status), every linked entity/document (with tier and status), and
    enough on every fact reference to click through to its source
    (via GET /api/v1/facts/{fact_id}, T53).
    """
    node = await db.get(EntityNode, node_id)
    if not node or node.tenant_id != tenant_id:
        raise HTTPException(status_code=404, detail="Entity not found")

    # --- Records this entity is the subject of (T60: versions + status) ---
    records_res = await db.execute(
        select(Record).where(Record.tenant_id == tenant_id, Record.subject_node_id == node_id)
    )
    records = list(records_res.scalars().all())
    records_out = []
    for record in records:
        current = await get_current_state(db, tenant_id, record.id)
        original = await get_original_state(db, tenant_id, record.id)
        records_out.append({
            "record_id": str(record.id),
            "record_type": record.record_type,
            "current": {
                "fields": current["fields"],
                "legal_status": current["legal_status"],
                "field_provenance": {
                    field: {**prov, "amendment_id": str(prov["amendment_id"]) if prov.get("amendment_id") else None,
                            "evidence_fact_id": str(prov["evidence_fact_id"]) if prov.get("evidence_fact_id") else None}
                    for field, prov in current["field_provenance"].items()
                },
            },
            "original": {"fields": original["fields"], "legal_status": original["legal_status"]},
        })

    # --- Edges touching this node, both directions ---
    edges_res = await db.execute(
        select(EntityEdge).where(
            EntityEdge.tenant_id == tenant_id,
            or_(
                EntityEdge.source_node_id == node_id,
                and_(EntityEdge.target_type == "entity", EntityEdge.target_node_id == node_id),
            ),
        )
    )
    edges = list({e.id: e for e in edges_res.scalars().all()}.values())  # dedupe self-loops

    other_node_ids = set()
    fact_ids = set()
    for e in edges:
        if e.source_node_id != node_id:
            other_node_ids.add(e.source_node_id)
        if e.target_type == "entity" and e.target_node_id and e.target_node_id != node_id:
            other_node_ids.add(e.target_node_id)
        if e.target_type == "fact" and e.target_fact_id:
            fact_ids.add(e.target_fact_id)

    other_nodes_by_id = {}
    if other_node_ids:
        res = await db.execute(select(EntityNode).where(EntityNode.id.in_(other_node_ids)))
        other_nodes_by_id = {n.id: n for n in res.scalars().all()}

    facts_by_id = {}
    docs_by_id = {}
    if fact_ids:
        res = await db.execute(select(Fact).where(Fact.id.in_(fact_ids)))
        facts_by_id = {f.id: f for f in res.scalars().all()}
        doc_ids = {f.document_id for f in facts_by_id.values()}
        if doc_ids:
            res2 = await db.execute(select(Document).where(Document.id.in_(doc_ids)))
            docs_by_id = {d.id: d for d in res2.scalars().all()}

    linked_entities = []
    linked_facts = []
    for e in edges:
        direction = "outgoing" if e.source_node_id == node_id else "incoming"
        base = {
            "edge_id": str(e.id),
            "edge_type": e.edge_type,
            "tier": e.tier,
            "status": e.status,
            "confidence": e.confidence,
            "direction": direction,
            "evidence_fact_id": str(e.evidence_fact_id) if e.evidence_fact_id else None,
        }
        if e.target_type == "entity":
            other_id = e.target_node_id if direction == "outgoing" else e.source_node_id
            other = other_nodes_by_id.get(other_id)
            if other:
                linked_entities.append({
                    **base,
                    "other_node": {"id": str(other.id), "entity_type": other.entity_type, "label": other.label},
                })
        elif e.target_type == "fact" and direction == "outgoing":
            fact = facts_by_id.get(e.target_fact_id)
            if fact:
                doc = docs_by_id.get(fact.document_id)
                linked_facts.append({
                    **base,
                    "fact": {
                        "fact_id": str(fact.id),
                        "field_name": fact.field_name,
                        "value": fact.value,
                        "document_id": str(fact.document_id),
                        "document_title": doc.title if doc else None,
                    },
                })

    return {
        "node": {"id": str(node.id), "entity_type": node.entity_type, "label": node.label, "attributes": node.attributes},
        "records": records_out,
        "linked_entities": linked_entities,
        "linked_facts": linked_facts,
    }
