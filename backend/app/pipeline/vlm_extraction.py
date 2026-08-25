"""T22 — VLM extraction path.

The chunker (T05) keeps word boxes for running text, but a scanned
register — multi-column tables, ditto marks, entries that wrap across two
pages — needs an actual look at the page image to read correctly, not just
a text dump. This module renders each page, asks a vision-language model
to read it against a registered Template's field schema (T24), runs the
result through the four record handlers (T26-T29) where the template says
to, and writes one Fact + FactRegion per field per row so every value is
click-through-able back to the exact spot it was read from (T06 contract).

Two-page spread joins (Handler 1, T26 — a register entry split across
facing pages, matched by serial number via join_spread()) are wired via
Template.layout == "spread" and _extract_spread_facts(). The left/right
field convention it reads is a best-effort invention, not modeled on a
real scanned spread — no seeded template exists yet (T25 stays blocked
on A1, no reference corpus) — flagged for revalidation once one is
available, not a confirmed real-world shape. A page pair that can't be
matched by serial writes a field_name="_join_mismatch" Fact for a human
to look at, same reused-facts pattern T30 used for marginalia.

Document classification (T23) is now a separate stage
(app/services/classification_service.py) that runs unconditionally at
ingest and persists its result on the document, rather than the ad-hoc
unpersisted match this module used to do inline. worker.py calls it first
and passes the resolved template in here.

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

from app.ai.factory import get_vlm_provider
from app.config import settings
from app.models.fact import Fact
from app.models.fact_region import FactRegion
from app.models.page import DocumentPage
from app.models.template import Template
from app.pipeline.handlers.blob_cell_parser import parse_blob_cell
from app.pipeline.handlers.continuation_merge import merge_continuation_rows
from app.pipeline.handlers.ditto_chain import expand_ditto_chains
from app.services.template_service import classify_confidence

logger = logging.getLogger(__name__)

RENDERABLE_EXTENSIONS = {"pdf", "jpg", "jpeg", "png", "bmp", "webp", "tiff"}

# Per-template field_schema convention this module reads (on top of T24's
# name/type/required/validation keys), all optional:
#   "role": "serial"             — the row-number column continuation-merge keys off
#   "role": "continuation_text"  — text column(s) a continuation row's text merges into
#   "ditto_eligible": true       — this column may carry a ditto mark to expand
#   "type": "blob"               — free-text cell to run through parse_blob_cell




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
        '"bbox": [x0,y0,x1,y1], "confidence": <0.0-1.0>, "is_handwritten": <bool>}, ... } ], '
        '"marginalia": [ {"text": <string>, "bbox": [x0,y0,x1,y1]}, ... ]}\n\n'
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
        "- Never invent a row or a value that is not visibly written on the page.\n"
        "- \"is_handwritten\" is true when THAT SPECIFIC VALUE is handwritten (pen/pencil "
        "ink) rather than printed/typed — set it per field, not per page; a printed form "
        "with one handwritten entry has is_handwritten=false on every other field.\n"
        "- \"marginalia\": any handwritten note, stamp annotation, or remark on the page "
        "that is NOT an answer to one of the schema's fields (e.g. a note in the margin, "
        "an interlineation, a struck-through correction) — each with its own bbox. Do not "
        "put marginalia text into a field's value.\n\n"
        f"Field schema:\n{json.dumps(schema_for_prompt, ensure_ascii=False)}"
    )


def _parse_vlm_response(raw: str) -> tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    text = raw.strip()
    if text.startswith("```"):
        text = text.split("```")[1]
        if text.startswith("json"):
            text = text[4:]
    data = json.loads(text.strip())
    rows = data.get("rows", [])
    marginalia = data.get("marginalia", [])
    return (
        rows if isinstance(rows, list) else [],
        marginalia if isinstance(marginalia, list) else [],
    )


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


async def _extract_spread_facts(
    db: AsyncSession, tenant_id: UUID, document_id: UUID, version_id: UUID,
    file_bytes: bytes, ext: str, vlm, field_schema: List[dict], max_pages: int,
) -> int:
    """T26 — join_spread() wiring: a spread-layout register's entry runs
    across two facing pages, matched and merged by serial number.

    The left/right convention this reads from field_schema (a field's
    "half": "left"|"right" key; the role:"serial" field is asked on both
    sides, since join_spread() matches on it) is an invented mechanism,
    not modeled on a real scanned spread — no seeded template exists yet
    (T25 stays blocked on A1, no reference corpus). Treat this as a
    best-effort capability to revalidate against real layouts once one
    is available, not a confirmed real-world shape.

    Deliberately does not run continuation-merge, ditto-chain, or
    blob-cell parsing on top of this — stacking those handlers on an
    unvalidated layout guess would compound one speculative assumption
    on another. A page-pair a template can't match by serial number
    writes a Fact+FactRegion under the field_name="_join_mismatch"
    sentinel (same reused-facts pattern T30 used for marginalia),
    anchored to the left page's full extent — there's no finer-grained
    region for a whole-pair structural mismatch.
    """
    from app.pipeline.handlers.spread_join import join_spread

    serial_field = _find_role_field(field_schema, "serial")
    if not serial_field:
        logger.warning("T26 spread template has no role:'serial' field — cannot pair pages by serial, skipping")
        return 0

    left_fields = [f for f in field_schema if f.get("half") == "left" or f["name"] == serial_field]
    right_fields = [f for f in field_schema if f.get("half") == "right" or f["name"] == serial_field]
    left_prompt = _build_extraction_prompt(left_fields)
    right_prompt = _build_extraction_prompt(right_fields)

    def _to_plain(rows: List[dict]) -> List[dict]:
        plain = []
        for row in rows:
            p = {k: (v.get("value") if isinstance(v, dict) else v) for k, v in row.items()}
            p["no"] = p.pop(serial_field, None)
            plain.append(p)
        return plain

    facts_written = 0

    for left_page_number in range(1, max_pages, 2):
        right_page_number = left_page_number + 1
        if right_page_number > max_pages:
            logger.warning(f"T26 spread template: page {left_page_number} has no matching right-hand page, skipping")
            break

        try:
            if ext == "pdf":
                left_rendered = _render_pdf_page_png(file_bytes, left_page_number)
                right_rendered = _render_pdf_page_png(file_bytes, right_page_number)
            else:
                # A standalone image is one page — a spread needs two, so
                # there's nothing to pair for a non-PDF upload.
                left_rendered = right_rendered = None
            if left_rendered is None or right_rendered is None:
                continue
            left_png, left_w, left_h, left_rot = left_rendered
            right_png, right_w, right_h, right_rot = right_rendered

            left_raw = await vlm.extract_structured(left_png, left_prompt)
            right_raw = await vlm.extract_structured(right_png, right_prompt)
            left_rows, _ = _parse_vlm_response(left_raw)
            right_rows, _ = _parse_vlm_response(right_raw)
            if not left_rows or not right_rows:
                continue

            left_plain = _to_plain(left_rows)
            right_plain = _to_plain(right_rows)
            left_by_serial_raw = {p["no"]: raw for p, raw in zip(left_plain, left_rows) if p.get("no") not in (None, "")}
            right_by_serial_raw = {p["no"]: raw for p, raw in zip(right_plain, right_rows) if p.get("no") not in (None, "")}

            result = join_spread(left_plain, right_plain)

            left_page = await _get_or_create_page(db, tenant_id, document_id, version_id, left_page_number, left_w, left_h, left_rot)

            if result.status == "needs_review":
                fact = Fact(
                    tenant_id=tenant_id, document_id=document_id, version_id=version_id,
                    field_name="_join_mismatch",
                    value={"reason": result.reason, "left_page": left_page_number, "right_page": right_page_number},
                    confidence=None, is_handwritten=False, status="in_review",
                )
                db.add(fact)
                await db.flush()
                db.add(FactRegion(tenant_id=tenant_id, fact_id=fact.id, page_id=left_page.id, x0=0.0, y0=0.0, x1=1.0, y1=1.0))
                facts_written += 1
                continue

            right_page = await _get_or_create_page(db, tenant_id, document_id, version_id, right_page_number, right_w, right_h, right_rot)

            for merged_row in result.rows:
                serial = merged_row.get("no")
                for field_def in field_schema:
                    field_name = field_def["name"]
                    if field_name == serial_field:
                        continue
                    value = merged_row.get(field_name)
                    if value is None or value == "":
                        continue

                    half = field_def.get("half")
                    raw_row = (left_by_serial_raw if half == "left" else right_by_serial_raw).get(serial)
                    if raw_row is None:
                        continue
                    src_field = raw_row.get(field_name)
                    if not isinstance(src_field, dict) or not src_field.get("bbox"):
                        continue

                    src_confidence = src_field.get("confidence")
                    src_confidence = float(src_confidence) if src_confidence is not None else None
                    src_is_handwritten = bool(src_field.get("is_handwritten"))

                    fact = Fact(
                        tenant_id=tenant_id, document_id=document_id, version_id=version_id,
                        field_name=field_name,
                        value=value if isinstance(value, (dict, list)) else {"v": value},
                        confidence=src_confidence,
                        is_handwritten=src_is_handwritten,
                        status=classify_confidence(field_def, src_confidence, is_handwritten=src_is_handwritten),
                    )
                    db.add(fact)
                    await db.flush()
                    x0, y0, x1, y1 = src_field["bbox"]
                    db.add(FactRegion(
                        tenant_id=tenant_id, fact_id=fact.id,
                        page_id=(left_page if half == "left" else right_page).id,
                        x0=float(x0), y0=float(y0), x1=float(x1), y1=float(y1),
                    ))
                    facts_written += 1

        except Exception as e:
            logger.warning(f"T26 spread extraction failed on pages {left_page_number}-{right_page_number}: {e}")
            continue

    return facts_written


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
    max_pages = min(len(pages_text), settings.vlm_max_pages_per_document)

    if template.layout == "spread":
        return await _extract_spread_facts(db, tenant_id, document_id, version_id, file_bytes, ext, vlm, field_schema, max_pages)

    prompt = _build_extraction_prompt(field_schema)
    serial_field = _find_role_field(field_schema, "serial")
    continuation_text_fields = [f["name"] for f in field_schema if f.get("role") == "continuation_text"]
    ditto_fields = [f["name"] for f in field_schema if f.get("ditto_eligible")]
    blob_fields = [f["name"] for f in field_schema if f.get("type") == "blob"]

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
            rows, marginalia = _parse_vlm_response(raw_response)
            if not rows and not marginalia:
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
                    field_is_handwritten = False
                    for src_idx in source_indices:
                        if src_idx >= len(rows):
                            continue
                        src_field = rows[src_idx].get(field_name)
                        if isinstance(src_field, dict) and src_field.get("bbox"):
                            region_boxes.append(src_field["bbox"])
                            if src_field.get("confidence") is not None:
                                confidences.append(float(src_field["confidence"]))
                            if src_field.get("is_handwritten"):
                                field_is_handwritten = True
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

                    fact_confidence = (sum(confidences) / len(confidences)) if confidences else None
                    fact = Fact(
                        tenant_id=tenant_id,
                        document_id=document_id,
                        version_id=version_id,
                        field_name=field_name,
                        value=fact_value if isinstance(fact_value, (dict, list)) else {"v": fact_value},
                        confidence=fact_confidence,
                        is_handwritten=field_is_handwritten,
                        status=classify_confidence(field_def, fact_confidence, is_handwritten=field_is_handwritten),
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

            # T30 — marginalia: handwritten notes that aren't an answer to any
            # schema field. Reuses Fact+FactRegion (T06's click-through contract)
            # rather than a separate table; field_name="_marginalia" is the
            # sentinel get_adjudication_queue's 'marginalia' category filters on.
            # Always in_review — there's no confidence band for "is this note
            # important," a human reads every one.
            for note in marginalia:
                text = note.get("text")
                bbox = note.get("bbox")
                if not text or not bbox or len(bbox) != 4:
                    continue
                fact = Fact(
                    tenant_id=tenant_id,
                    document_id=document_id,
                    version_id=version_id,
                    field_name="_marginalia",
                    value={"v": text},
                    confidence=None,
                    is_handwritten=True,
                    status="in_review",
                )
                db.add(fact)
                await db.flush()
                x0, y0, x1, y1 = bbox
                db.add(FactRegion(
                    tenant_id=tenant_id, fact_id=fact.id, page_id=page.id,
                    x0=float(x0), y0=float(y0), x1=float(x1), y1=float(y1),
                ))
                facts_written += 1

        except Exception as e:
            logger.warning(f"T22 VLM extraction failed on page {page_number} of {filename}: {e}")
            continue

    return facts_written
