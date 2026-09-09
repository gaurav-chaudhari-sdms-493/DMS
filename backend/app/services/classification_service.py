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


MATCH_TEMPLATE_ATTEMPTS = 3


async def match_template(db: AsyncSession, sample_text: str) -> Optional[Template]:
    """Best-effort LLM match against every registered template. Returns
    None (not an error) when nothing is registered yet, or nothing matches.

    Live bug, 2026-09-04: max_tokens=512 was sized for a small template
    list. Confirmed live: with 5 templates registered, Groq's reasoning
    model (gpt-oss) regularly spends its ENTIRE 512-token budget on hidden
    <think> reasoning about which of the 5 options fits, leaving zero
    tokens for the visible one-line answer -- llm.complete() returns "",
    which this function was silently treating as "no match" (indistinguishable
    from a genuine non-match). Reproduced 3/3 on a real Wakf gazette cover
    page that plainly matches one of the registered templates; the LLM
    answers correctly every time once given real headroom (2000 tokens).
    This is why classify_document leaves the vast majority of real uploads
    'unclassified' -- confirmed live against this DB: 1732 of 1753
    documents (98.8%) are unclassified, and every one of them skips T22
    (VLM extraction) and TS1 (stitching) entirely, since worker.py only
    runs that stage when classification succeeds.

    Retries up to MATCH_TEMPLATE_ATTEMPTS times on top of the larger
    budget: the same resilience pattern already used for
    table_stitch.adjudicate_structure's reasoning-model calls (see that
    function's docstring and [[feedback_colleague_project_inspiration_only]])
    -- a reasoning model can still return an empty or unparseable reply on
    one attempt and a clean one on the next, so a single try turns
    ordinary flakiness into a silent, wrong "no template matches" too.

    2026-09-07: the empty-response retry above closed the token-starvation
    bug, but a second, narrower flakiness remained -- confirmed live by
    sampling 4 calls against a plainly-matching real document, 1 of the 4
    confidently answered NONE. That's a *non-empty*, cleanly-parseable
    response, so the old "retry only on empty resp" loop accepted it as
    final on attempt 1 every time it happened to land first. Never
    observed the opposite failure (confidently naming the WRONG template)
    in any sampling done so far -- the risk here is real documents being
    silently lost to 'unclassified' (as the 98.8% incident showed), not
    documents being misfiled under a wrong template. So a positive match
    is trusted the instant any attempt produces one (unchanged fast path
    for the common "it matches" case), but a NONE only becomes the final
    answer once every attempt in the budget agrees on it -- one attempt's
    NONE no longer ends the loop early. This does mean a genuinely
    unclassified document (most real uploads -- budgets, memos, anything
    that isn't a registered form -- see this module's own top docstring)
    now costs the full MATCH_TEMPLATE_ATTEMPTS calls instead of one, since
    there's no way to distinguish "confidently no match" from "flakily no
    match" without asking again. That's the same worst-case call budget
    the empty-response retry already allowed for, just now typical for
    negatives too -- accepted as the cost of not silently dropping real
    matches."""
    res = await db.execute(select(Template))
    templates = list(res.scalars().all())
    if not templates:
        return None

    options = [f"{t.form_type} | {t.era_label}" for t in templates]
    prompt = (
        "A scanned government document starts with this text:\n\n"
        # 4000, not the old 1500: the caller now concatenates the first few
        # pages (worker.py), not just page 1, because the form-identifying
        # content (e.g. a "Form B" header + its column names) routinely
        # doesn't appear until page 2+ of a multi-page gazette whose page 1
        # is shared boilerplate. A budget sized for one page silently
        # truncated that content back out even after the caller fetched it.
        f"{sample_text[:4000]}\n\n"
        "Which of these registered form templates, if any, does it match?\n"
        + "\n".join(f"- {o}" for o in options)
        + "\n\nMatch on what the document itself IS — its own form designation "
          "(e.g. \"Form B\"), the district/date printed in ITS header or table, and "
          "its column layout — never on the name or city of the office that issued "
          "or published it. A publishing office's name is often repeated many times "
          "as boilerplate and can cover documents about many other districts/years/"
          "forms; it is not evidence of a match by itself. If the document's own "
          "form designation, district or year conflicts with a candidate's era_label, "
          "that candidate is NOT a match even if the issuing office's name lines up.\n\n"
          "Reply with ONLY the exact 'form_type | era_label' string of the best match, "
          "or the single word NONE if it doesn't match any of them."
    )

    for _attempt in range(MATCH_TEMPLATE_ATTEMPTS):
        try:
            llm = get_llm_provider()
            # max_tokens has real headroom beyond the one-line answer: a
            # reasoning model's hidden thinking tokens scale with how many
            # options it's weighing, not just the answer length -- see the
            # docstring above for the live-confirmed failure at 512.
            resp = (await llm.complete([Message(role="user", content=prompt)], temperature=0.0, max_tokens=2000)).strip()
        except Exception:
            resp = ""
        if not resp:
            continue  # no usable response this attempt -- try again

        resp_last_line = resp.strip().splitlines()[-1].strip().strip('"')
        for t, option in zip(templates, options):
            if resp_last_line == option or option in resp_last_line:
                return t  # a positive match is trusted on the first attempt that finds one

        # Parsed cleanly but named no template (typically "NONE") -- don't
        # trust a single no-match answer; keep going and only fall through
        # to `return None` below once every attempt in the budget agrees.

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
