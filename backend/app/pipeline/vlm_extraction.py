"""T22 — VLM extraction path.

The chunker (T05) keeps word boxes for running text, but a scanned
register — multi-column tables, ditto marks, entries that wrap across two
pages — needs an actual look at the page image to read correctly, not just
a text dump. This module renders each page, asks a vision-language model
to read it against a registered Template's field schema (T24), runs the
result through the four record handlers (T26-T29) where the template says
to, and writes one Fact + FactRegion per field per row so every value is
click-through-able back to the exact spot it was read from (T06 contract).

Two things this deliberately does NOT do yet:
  - Two-page spread joins (Handler 1, T26). Pairing "left half / right half"
    pages is genuinely template-specific (which pages are a spread, and in
    what order) and no seeded template declares it yet (T25 is blocked on
    A1 — no real reference corpus to model one on). join_spread() is wired
    up and ready; nothing calls it until a template opts in.
  - Document classification (T23). select_template_for_document() below is
    a light best-effort match against whatever templates exist, using the
    existing text LLM — not the classification stage + unclassified queue
    T23 actually specifies. When no template matches (or none are
    registered, which is the case until T25/A1 lands), extraction is
    skipped and the document stays chunk-only-indexed, same as before this
    task existed.

Best-effort by design: a VLM failure never fails ingestion. Search and
chunk indexing must never wait on this (Section 3.5), so every call site
wraps this module in a try/except and logs, it doesn't raise.
"""
import base64
import io
import json
import logging
from typing import Any, Dict, List, Optional
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.base import Message
from app.ai.factory import get_llm_provider, get_vlm_provider
from app.config import settings
from app.models.fact import Fact
from app.models.fact_region import FactRegion
from app.models.page import DocumentPage
from app.models.template import Template
from app.pipeline.handlers.blob_cell_parser import parse_blob_cell
from app.pipeline.handlers.continuation_merge import merge_continuation_rows
from app.pipeline.handlers.ditto_chain import expand_ditto_chains

logger = logging.getLogger(__name__)

RENDERABLE_EXTENSIONS = {"pdf", "jpg", "jpeg", "png", "bmp", "webp", "tiff"}

# Per-template field_schema convention this module reads (on top of T24's
# name/type/required/validation keys), all optional:
#   "role": "serial"             — the row-number column continuation-merge keys off
#   "role": "continuation_text"  — text column(s) a continuation row's text merges into
#   "ditto_eligible": true       — this column may carry a ditto mark to expand
#   "type": "blob"               — free-text cell to run through parse_blob_cell


async def select_template_for_document(db: AsyncSession, sample_text: str) -> Optional[Template]:
    """Best-effort template match — see module docstring: this is not T23."""
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
    except Exception as e:
        logger.warning(f"T22 template match call failed: {e}")
        return None

    resp_last_line = resp.strip().splitlines()[-1].strip().strip('"') if resp.strip() else ""
    for t, option in zip(templates, options):
        if resp_last_line == option or option in resp_last_line:
            return t
    return None


def _render_pdf_page_png(file_bytes: bytes, page_number: int) -> Optional[tuple[bytes, float, float, float]]:
    """Returns (png_bytes, width, height, rotation) for one 1-indexed PDF page, or None."""
    import pdfplumber
    with pdfplumber.open(io.BytesIO(file_bytes)) as pdf:
        if page_number - 1 >= len(pdf.pages):
            return None
        page = pdf.pages[page_number - 1]
        img = page.to_image(resolution=150).original
        buf = io.BytesIO()
        img.save(buf, format="PNG")
        rotation = float(getattr(page, "rotation", 0) or 0)
        return buf.getvalue(), float(page.width), float(page.height), rotation


def _render_image_page_png(file_bytes: bytes) -> tuple[bytes, float, float, float]:
    from PIL import Image
    img = Image.open(io.BytesIO(file_bytes))
    width, height = img.size
    buf = io.BytesIO()
    img.convert("RGB").save(buf, format="PNG")
    return buf.getvalue(), float(width), float(height), 0.0


def _build_extraction_prompt(field_schema: List[dict]) -> str:
    schema_for_prompt = [
        {"name": f["name"], "type": f.get("type", "string"), "required": f.get("required", False)}
        for f in field_schema
    ]
    return (
        "You are reading one page of a scanned government register. Return ONLY valid JSON "
        "(no markdown fences) shaped exactly like this:\n"
        '{"rows": [ { "<field_name>": {"value": <string|number|null>, '
        '"bbox": [x0,y0,x1,y1], "confidence": <0.0-1.0>}, ... } ]}\n\n'
        "Rules:\n"
        "- One entry in \"rows\" per data row visible on this page (a page with a single "
        "form, not a table, still produces exactly one row).\n"
        "- bbox is [x0,y0,x1,y1], each a fraction from 0.0 to 1.0 of the page's width/height. "
        "The ORIGIN is the page's TOP-LEFT corner: x grows right, y grows DOWN.\n"
        "- If a cell literally contains a ditto mark (e.g. \",,\", '\"', \"do\", \"-do-\") "
        "meaning 'same as the row above', return that literal mark as the value — do not "
        "resolve it to the value above yourself.\n"
        "- If a row's serial number is blank because the row is just wrapped continuation "
        "text from the entry above, return \"\" for that field.\n"
        "- If a field from the schema is not present anywhere on this page, omit its key "
        "from that row entirely rather than guessing a value.\n"
        "- Never invent a row or a value that is not visibly written on the page.\n\n"
        f"Field schema:\n{json.dumps(schema_for_prompt, ensure_ascii=False)}"
    )


def _parse_vlm_response(raw: str) -> List[Dict[str, Any]]:
    text = raw.strip()
    if text.startswith("```"):
        text = text.split("```")[1]
        if text.startswith("json"):
            text = text[4:]
    data = json.loads(text.strip())
    rows = data.get("rows", [])
    return rows if isinstance(rows, list) else []


def _find_role_field(field_schema: List[dict], role: str) -> Optional[str]:
    for f in field_schema:
        if f.get("role") == role:
            return f["name"]
    return None


async def _get_or_create_page(
    db: AsyncSession, tenant_id: UUID, document_id: UUID, version_id: UUID,
    page_number: int, width: float, height: float, rotation: float,
) -> DocumentPage:
    res = await db.execute(
        select(DocumentPage).where(
            DocumentPage.document_id == document_id,
            DocumentPage.version_id == version_id,
            DocumentPage.page_number == page_number,
        )
    )
    page = res.scalar_one_or_none()
    if page:
        return page
    page = DocumentPage(
        tenant_id=tenant_id, document_id=document_id, version_id=version_id,
        page_number=page_number, width=width, height=height,
        rotation=rotation, skew=0.0,  # deskew detection is a separate, not-yet-built pass
    )
    db.add(page)
    await db.flush()
    return page


async def extract_facts_for_document(
    db: AsyncSession,
    tenant_id: UUID,
    document_id: UUID,
    version_id: UUID,
    file_bytes: bytes,
    filename: str,
    pages_text: List[dict],
    template: Template,
) -> int:
    """Runs VLM extraction across a document's pages against one template.
    Returns the number of facts written. Raises on hard failure — callers
    are expected to catch and log, never let this fail ingestion."""
    vlm = get_vlm_provider()
    if vlm is None:
        return 0

    ext = filename.lower().rsplit(".", 1)[-1] if "." in filename else ""
    if ext not in RENDERABLE_EXTENSIONS:
        return 0

    field_schema = template.field_schema
    prompt = _build_extraction_prompt(field_schema)
    serial_field = _find_role_field(field_schema, "serial")
    continuation_text_fields = [f["name"] for f in field_schema if f.get("role") == "continuation_text"]
    ditto_fields = [f["name"] for f in field_schema if f.get("ditto_eligible")]
    blob_fields = [f["name"] for f in field_schema if f.get("type") == "blob"]

    max_pages = min(len(pages_text), settings.vlm_max_pages_per_document)
    facts_written = 0

    for page_number in range(1, max_pages + 1):
        try:
            if ext == "pdf":
                rendered = _render_pdf_page_png(file_bytes, page_number)
                if rendered is None:
                    continue
                png_bytes, width, height, rotation = rendered
            else:
                if page_number > 1:
                    break
                png_bytes, width, height, rotation = _render_image_page_png(file_bytes)

            raw_response = await vlm.extract_structured(png_bytes, prompt)
            rows = _parse_vlm_response(raw_response)
            if not rows:
                continue

            # Continuation-merge (Handler 3) needs the serial column present to know
            # which rows are continuations; skip it for templates that don't declare one.
            if serial_field:
                plain_rows = [
                    {k: (v.get("value") if isinstance(v, dict) else v) for k, v in row.items()}
                    for row in rows
                ]
                # Normalize to the handler's expected "no" key without mutating the template.
                for plain, row in zip(plain_rows, rows):
                    plain["no"] = plain.pop(serial_field, None)
                try:
                    merged_plain = merge_continuation_rows(plain_rows, text_columns=continuation_text_fields or None)
                except ValueError as e:
                    logger.warning(f"T22 continuation-merge skipped for page {page_number}: {e}")
                    merged_plain = [{**p, "_source_row_indices": [i]} for i, p in enumerate(plain_rows)]
            else:
                merged_plain = [{**{k: (v.get("value") if isinstance(v, dict) else v) for k, v in row.items()}, "_source_row_indices": [i]} for i, row in enumerate(rows)]

            if ditto_fields:
                try:
                    merged_plain = expand_ditto_chains(merged_plain, ditto_fields)
                except ValueError as e:
                    logger.warning(f"T22 ditto-chain expansion skipped for page {page_number}: {e}")

            page = await _get_or_create_page(db, tenant_id, document_id, version_id, page_number, width, height, rotation)

            for merged_row in merged_plain:
                source_indices = merged_row.get("_source_row_indices", [])
                if not source_indices:
                    continue
                for field_def in field_schema:
                    field_name = field_def["name"]
                    row_key = "no" if field_name == serial_field else field_name
                    if row_key not in merged_row:
                        continue
                    value = merged_row[row_key]
                    if value is None or value == "":
                        continue

                    confidences = []
                    region_boxes = []
                    for src_idx in source_indices:
                        if src_idx >= len(rows):
                            continue
                        src_field = rows[src_idx].get(field_name)
                        if isinstance(src_field, dict) and src_field.get("bbox"):
                            region_boxes.append(src_field["bbox"])
                            if src_field.get("confidence") is not None:
                                confidences.append(float(src_field["confidence"]))
                    if not region_boxes:
                        continue

                    fact_value: Any = value
                    if field_name in blob_fields and isinstance(value, str):
                        parsed = parse_blob_cell(value)
                        fact_value = {
                            "raw_text": parsed.raw_text,
                            "survey_numbers": parsed.survey_numbers,
                            "cts": parsed.cts,
                            "area_sqm": parsed.area_sqm,
                            "built_sqm": parsed.built_sqm,
                            "open_space_sqm": parsed.open_space_sqm,
                            "flags": parsed.flags,
                        }

                    fact = Fact(
                        tenant_id=tenant_id,
                        document_id=document_id,
                        version_id=version_id,
                        field_name=field_name,
                        value=fact_value if isinstance(fact_value, (dict, list)) else {"v": fact_value},
                        confidence=(sum(confidences) / len(confidences)) if confidences else None,
                    )
                    db.add(fact)
                    await db.flush()

                    for box in region_boxes:
                        x0, y0, x1, y1 = box
                        db.add(FactRegion(
                            tenant_id=tenant_id, fact_id=fact.id, page_id=page.id,
                            x0=float(x0), y0=float(y0), x1=float(x1), y1=float(y1),
                        ))
                    facts_written += 1

        except Exception as e:
            logger.warning(f"T22 VLM extraction failed on page {page_number} of {filename}: {e}")
            continue

    return facts_written
