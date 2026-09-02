"""T23 — document classification stage + unclassified queue.

Runs unconditionally at ingest, regardless of whether VLM extraction
(T22) is even enabled — classification is "does this document match a
registered form template," a separate question from "read it with a
vision model." Persists the answer on the document instead of
recomputing and discarding it, which is what T22 did before this task.

'unclassified' is the default resting state, not an error: most
documents (budgets, financial analyses, ...) are not statutory forms and
never will be. The queue this module exposes is for a person to either
manually assign a template the automatic match missed, or dismiss a
document as genuinely not needing one — either way it stops sitting in
'unclassified' forever.
"""
from typing import Any, Dict, Optional
from uuid import UUID

from fastapi import HTTPException
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.base import Message
from app.ai.factory import get_llm_provider
from app.models.document import Document
from app.models.template import Template
from app.services.audit_service import log_action


async def match_template(db: AsyncSession, sample_text: str) -> Optional[Template]:
    """Best-effort LLM match against every registered template. Returns
    None (not an error) when nothing is registered yet, or nothing matches."""
    res = await db.execute(select(Template))
    templates = list(res.scalars().all())
    if not templates:
        return None

    options = [f"{t.form_type} | {t.era_label}" for t in templates]
    prompt = (
        "A scanned government document starts with this text:\n\n"
        f"{sample_text[:1500]}\n\n"
        "Which of these registered form templates, if any, does it match?\n"
        + "\n".join(f"- {o}" for o in options)
        + "\n\nReply with ONLY the exact 'form_type | era_label' string of the best match, "
          "or the single word NONE if it doesn't match any of them."
    )
    try:
        llm = get_llm_provider()
        # max_tokens has headroom beyond the one-line answer: reasoning models
        # (e.g. Groq's gpt-oss) spend part of the budget on hidden reasoning
        # tokens before the visible answer, so a tight limit here returns "".
        resp = (await llm.complete([Message(role="user", content=prompt)], temperature=0.0, max_tokens=512)).strip()
    except Exception:
        return None

    resp_last_line = resp.strip().splitlines()[-1].strip().strip('"') if resp.strip() else ""
    for t, option in zip(templates, options):
        if resp_last_line == option or option in resp_last_line:
            return t
    return None


async def classify_document(db: AsyncSession, tenant_id: UUID, document_id: UUID, sample_text: str) -> Document:
    """The automatic classification stage — called from the ingestion
    pipeline. Never raises on a no-match; that's the normal case."""
    doc = await db.get(Document, document_id)
    if not doc or doc.tenant_id != tenant_id:
        raise HTTPException(status_code=404, detail="Document not found")

    template = await match_template(db, sample_text)
    if template:
        doc.classification_status = "classified"
        doc.matched_template_id = template.id
    else:
        doc.classification_status = "unclassified"
        doc.matched_template_id = None

    await db.flush()
    return doc


async def list_unclassified_documents(db: AsyncSession, tenant_id: UUID, limit: int = 50, offset: int = 0) -> Dict[str, Any]:
    count_res = await db.execute(
        select(func.count(Document.id)).where(
            Document.tenant_id == tenant_id, Document.classification_status == "unclassified"
        )
    )
    total = count_res.scalar() or 0

    res = await db.execute(
        select(Document)
        .where(Document.tenant_id == tenant_id, Document.classification_status == "unclassified")
        .order_by(Document.created_at.desc())
        .limit(limit).offset(offset)
    )
    docs = list(res.scalars().all())

    return {
        "total": total,
        "documents": [
            {"document_id": str(d.id), "title": d.title, "doc_type": d.doc_type, "created_at": d.created_at}
            for d in docs
        ],
    }


async def manually_classify_document(
    db: AsyncSession, tenant_id: UUID, document_id: UUID, template_id: UUID, actor_id: UUID,
) -> Document:
    """An operator assigns a template the automatic match missed."""
    doc = await db.get(Document, document_id)
    if not doc or doc.tenant_id != tenant_id:
        raise HTTPException(status_code=404, detail="Document not found")

    template = await db.get(Template, template_id)
    if not template:
        raise HTTPException(status_code=404, detail="Template not found")

    doc.classification_status = "classified"
    doc.matched_template_id = template.id
    await db.flush()

    await log_action(
        db, actor_id, tenant_id, "document.classify_manual",
        resource_type="document", resource_id=document_id,
        details={"template_id": str(template_id), "form_type": template.form_type, "era_label": template.era_label},
    )
    await db.commit()
    return doc


async def dismiss_document_classification(db: AsyncSession, tenant_id: UUID, document_id: UUID, actor_id: UUID) -> Document:
    """An operator confirms this document genuinely isn't a registered
    form type — stops it reappearing in the unclassified queue."""
    doc = await db.get(Document, document_id)
    if not doc or doc.tenant_id != tenant_id:
        raise HTTPException(status_code=404, detail="Document not found")

    doc.classification_status = "dismissed"
    doc.matched_template_id = None
    await db.flush()

    await log_action(
        db, actor_id, tenant_id, "document.classify_dismiss",
        resource_type="document", resource_id=document_id, details={},
    )
    await db.commit()
    return doc
