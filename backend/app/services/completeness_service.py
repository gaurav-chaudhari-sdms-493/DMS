"""T76 — completeness and reconciliation dashboard, gap-scored per corpus.

"Corpus" is a folder, same scoping T57/T59/T66 already use. Six things
this reports, matching the backlog line item exactly:
  - missing fields      — a classified document (T23) whose template
                           (T24) requires a field no Fact exists for.
  - failed pages         — doc_dg_documents.pages_failed_count (T76
                           migration; populated for every document at
                           ingest, not just template matches).
  - unverified rows       — facts still 'machine' or 'in_review' (never
                           reached 'verified' via T51).
  - machine-vs-verified split — Fact.status counts.
  - confidence distribution — bucketed histogram of Fact.confidence.
  - drill-through          — get_completeness_drill() returns the actual
                           rows behind any one number above.

Read-only throughout: this is a report, not a gate. Nothing here blocks
indexing or verification (Section 3.5).
"""
from typing import Any, Dict, List, Optional
from uuid import UUID

from fastapi import HTTPException
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.document import Document
from app.models.entity_edge import EntityEdge
from app.models.fact import Fact
from app.models.template import Template


def _folder_filter(corpus_folder_id: Optional[UUID]):
    """corpus_folder_id=None means the "root" corpus — documents with no
    folder at all, which were previously invisible to this dashboard since
    every query required an exact folder UUID."""
    if corpus_folder_id is None:
        return Document.folder_id.is_(None)
    return Document.folder_id == corpus_folder_id

CONFIDENCE_BUCKETS = [
    ("0.00-0.50", 0.0, 0.5),
    ("0.50-0.70", 0.5, 0.7),
    ("0.70-0.85", 0.7, 0.85),
    ("0.85-0.95", 0.85, 0.95),
    ("0.95-1.00", 0.95, 1.01),  # 1.01 so a fact at exactly 1.0 lands here
]


async def _find_missing_fields(db: AsyncSession, tenant_id: UUID, corpus_folder_id: Optional[UUID]) -> List[Dict[str, Any]]:
    res = await db.execute(
        select(Document.id, Document.title, Document.matched_template_id).where(
            Document.tenant_id == tenant_id,
            _folder_filter(corpus_folder_id),
            Document.classification_status == "classified",
            Document.matched_template_id.is_not(None),
        )
    )
    classified_docs = res.all()
    if not classified_docs:
        return []

    template_ids = {t_id for _, _, t_id in classified_docs}
    templates_res = await db.execute(select(Template).where(Template.id.in_(template_ids)))
    templates_by_id = {t.id: t for t in templates_res.scalars().all()}

    doc_ids = [d_id for d_id, _, _ in classified_docs]
    facts_res = await db.execute(
        select(Fact.document_id, Fact.field_name).where(Fact.tenant_id == tenant_id, Fact.document_id.in_(doc_ids))
    )
    fields_by_doc: Dict[UUID, set] = {}
    for doc_id, field_name in facts_res.all():
        fields_by_doc.setdefault(doc_id, set()).add(field_name)

    missing = []
    for doc_id, title, template_id in classified_docs:
        template = templates_by_id.get(template_id)
        if not template:
            continue
        present = fields_by_doc.get(doc_id, set())
        for field_def in template.field_schema:
            if field_def.get("required") and field_def["name"] not in present:
                missing.append({
                    "document_id": str(doc_id),
                    "document_title": title,
                    "template_id": str(template_id),
                    "field_name": field_def["name"],
                })
    return missing


async def get_corpus_completeness(db: AsyncSession, tenant_id: UUID, corpus_folder_id: Optional[UUID]) -> Dict[str, Any]:
    doc_res = await db.execute(
        select(
            func.count(Document.id),
            func.coalesce(func.sum(Document.pages_total_count), 0),
            func.coalesce(func.sum(Document.pages_failed_count), 0),
            func.count(Document.id).filter(Document.pages_failed_count > 0),
            func.coalesce(func.sum(Document.data_loss_words_missing), 0),
            func.count(Document.id).filter(Document.data_loss_words_missing > 0),
            func.count(Document.id).filter(Document.page_furniture_candidates.is_not(None)),
        ).where(Document.tenant_id == tenant_id, _folder_filter(corpus_folder_id), Document.is_trashed == False)  # noqa: E712
    )
    (
        document_count, pages_total, pages_failed, documents_with_failed_pages,
        data_loss_words_total, documents_with_data_loss, documents_with_furniture,
    ) = doc_res.one()

    fact_status_res = await db.execute(
        select(Fact.status, func.count(Fact.id))
        .join(Document, Fact.document_id == Document.id)
        .where(Fact.tenant_id == tenant_id, _folder_filter(corpus_folder_id))
        .group_by(Fact.status)
    )
    fact_status_counts = {status: count for status, count in fact_status_res.all()}

    conf_res = await db.execute(
        select(Fact.confidence)
        .join(Document, Fact.document_id == Document.id)
        .where(Fact.tenant_id == tenant_id, _folder_filter(corpus_folder_id), Fact.confidence.is_not(None))
    )
    confidences = [c for (c,) in conf_res.all()]
    histogram = []
    for label, low, high in CONFIDENCE_BUCKETS:
        histogram.append({"bucket": label, "count": sum(1 for c in confidences if low <= c < high)})

    edge_status_res = await db.execute(
        select(EntityEdge.status, func.count(EntityEdge.id))
        .join(Fact, EntityEdge.evidence_fact_id == Fact.id)
        .join(Document, Fact.document_id == Document.id)
        .where(EntityEdge.tenant_id == tenant_id, _folder_filter(corpus_folder_id))
        .group_by(EntityEdge.status)
    )
    edge_status_counts = {status: count for status, count in edge_status_res.all()}

    missing_fields = await _find_missing_fields(db, tenant_id, corpus_folder_id)

    return {
        "corpus_folder_id": str(corpus_folder_id) if corpus_folder_id else "root",
        "documents": {
            "total": document_count,
            "pages_total": pages_total,
            "pages_failed": pages_failed,
            "documents_with_failed_pages": documents_with_failed_pages,
        },
        "data_loss": {
            # TS2 — word-level audit between OCR and stored chunks (see
            # app/services/data_loss_audit.py), populated at ingest.
            "documents_with_loss": documents_with_data_loss,
            "total_missing_words": data_loss_words_total,
        },
        "page_furniture": {
            # TS6 — running header/footer candidates by position
            # stability (see app/services/page_furniture_service.py).
            # Detection only, informational.
            "documents_with_candidates": documents_with_furniture,
        },
        "facts": {
            "machine": fact_status_counts.get("machine", 0),
            "in_review": fact_status_counts.get("in_review", 0),
            "verified": fact_status_counts.get("verified", 0),
            "confidence_histogram": histogram,
        },
        "entity_edges": {
            "machine": edge_status_counts.get("machine", 0),
            "held": edge_status_counts.get("held", 0),
            "verified": edge_status_counts.get("verified", 0),
        },
        "missing_fields": {
            "count": len(missing_fields),
        },
    }


async def get_completeness_drill(db: AsyncSession, tenant_id: UUID, corpus_folder_id: Optional[UUID], category: str) -> List[Dict[str, Any]]:
    """Drill-through: the actual rows behind one completeness number."""
    if category == "missing_fields":
        return await _find_missing_fields(db, tenant_id, corpus_folder_id)

    if category == "failed_pages":
        res = await db.execute(
            select(Document.id, Document.title, Document.pages_total_count, Document.pages_failed_count).where(
                Document.tenant_id == tenant_id, _folder_filter(corpus_folder_id),
                Document.pages_failed_count > 0, Document.is_trashed == False,  # noqa: E712
            )
        )
        return [
            {"document_id": str(d_id), "document_title": title, "pages_total": total, "pages_failed": failed}
            for d_id, title, total, failed in res.all()
        ]

    if category == "data_loss_documents":
        res = await db.execute(
            select(Document.id, Document.title, Document.data_loss_words_missing, Document.data_loss_details).where(
                Document.tenant_id == tenant_id, _folder_filter(corpus_folder_id),
                Document.data_loss_words_missing > 0, Document.is_trashed == False,  # noqa: E712
            )
        )
        return [
            {"document_id": str(d_id), "document_title": title, "words_missing": missing, "details": details}
            for d_id, title, missing, details in res.all()
        ]

    if category == "page_furniture_documents":
        res = await db.execute(
            select(Document.id, Document.title, Document.page_furniture_candidates).where(
                Document.tenant_id == tenant_id, _folder_filter(corpus_folder_id),
                Document.page_furniture_candidates.is_not(None), Document.is_trashed == False,  # noqa: E712
            )
        )
        return [
            {"document_id": str(d_id), "document_title": title, "candidates": candidates}
            for d_id, title, candidates in res.all()
        ]

    if category in ("unverified_facts", "machine_facts"):
        status_filter = ["machine", "in_review"] if category == "unverified_facts" else ["machine"]
        res = await db.execute(
            select(Fact.id, Fact.document_id, Fact.field_name, Fact.value, Fact.confidence, Fact.status)
            .join(Document, Fact.document_id == Document.id)
            .where(Fact.tenant_id == tenant_id, _folder_filter(corpus_folder_id), Fact.status.in_(status_filter))
        )
        return [
            {"fact_id": str(f_id), "document_id": str(doc_id), "field_name": fn, "value": v, "confidence": c, "status": s}
            for f_id, doc_id, fn, v, c, s in res.all()
        ]

    raise HTTPException(status_code=400, detail=f"Unknown drill category '{category}'. Valid: missing_fields, failed_pages, data_loss_documents, page_furniture_documents, unverified_facts, machine_facts")
