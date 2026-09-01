"""T77 — on-demand summary report generation, exportable, unverified data flagged.

Builds on T78's gather_evidence_package() (same entity-evidence scope,
same D-8 confirmation_status labeling) but produces a narrative summary
instead of a raw tabular dump — the difference between an export and a
report per the backlog's own split between the two tasks.

The flagging is computed deterministically from confirmation_status, not
left to an LLM to decide — T70 already established the precedent for
this codebase: never trust free-form model output for a claim about
whether something is verified. Every unverified line is explicit,
"[UNVERIFIED — machine-suggested, not human-confirmed]", not a paraphrase
that could drop the caveat. Same audit-with-content-hash discipline as
T78's exports.
"""
import hashlib
import io
import json
from typing import Any, Dict, List, Tuple
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.services.audit_service import log_action
from app.services.export_service import ExportFormat, ExportMode, CONTENT_TYPES, gather_evidence_package

UNVERIFIED_TAG = "[UNVERIFIED — machine-suggested, not human-confirmed]"


def _build_summary_lines(data: Dict[str, Any]) -> List[str]:
    """Deterministic narrative — no LLM in this path. Every line sourced
    from an unverified edge/fact ends with UNVERIFIED_TAG, always, never
    conditionally on model judgment."""
    node = data["node"]
    lines = [f"Summary report for {node['label']} ({node['entity_type']}), generated {data['generated_at']}."]

    if not data["records"]:
        lines.append("No records exist for this entity.")
    for r in data["records"]:
        status = r["current"]["legal_status"] or "unspecified status"
        field_summary = ", ".join(f"{k}={v}" for k, v in r["current"]["fields"].items())
        lines.append(f"Record ({r['record_type']}, {status}): {field_summary}")

    verified_entities = [e for e in data["linked_entities"] if e["confirmation_status"] == "human_verified"]
    unverified_entities = [e for e in data["linked_entities"] if e["confirmation_status"] != "human_verified"]
    if verified_entities:
        for e in verified_entities:
            other = e.get("other_node", {}).get("label", "another entity")
            lines.append(f"Confirmed link: {e['edge_type']} — {other} (tier {e['tier']}, confidence {e['confidence']}).")
    if unverified_entities:
        for e in unverified_entities:
            other = e.get("other_node", {}).get("label", "another entity")
            lines.append(f"Suggested link: {e['edge_type']} — {other} (tier {e['tier']}, confidence {e['confidence']}). {UNVERIFIED_TAG}")
    if not data["linked_entities"]:
        lines.append("No linked entities.")

    verified_facts = [e for e in data["linked_facts"] if e["confirmation_status"] == "human_verified"]
    unverified_facts = [e for e in data["linked_facts"] if e["confirmation_status"] != "human_verified"]
    for e in verified_facts:
        f = e["fact"]
        lines.append(f"Confirmed fact: {f['field_name']} = {f['value']} (from {f.get('document_title') or 'unknown source'}).")
    for e in unverified_facts:
        f = e["fact"]
        lines.append(f"Suggested fact: {f['field_name']} = {f['value']} (from {f.get('document_title') or 'unknown source'}). {UNVERIFIED_TAG}")
    if not data["linked_facts"]:
        lines.append("No linked facts.")

    total_edges = len(data["linked_entities"])
    unverified_count = len(unverified_entities) + len(unverified_facts)
    total_items = total_edges + len(data["linked_facts"])
    if unverified_count:
        lines.append(f"{unverified_count} of {total_items} linked item(s) in this report are unverified and must not be treated as established fact.")

    return lines


def _to_json_bytes(lines: List[str], data: Dict[str, Any]) -> bytes:
    payload = {"summary_lines": lines, "evidence": data}
    return json.dumps(payload, indent=2, default=str).encode("utf-8")


def _to_text_bytes(lines: List[str]) -> bytes:
    return "\n".join(lines).encode("utf-8")


def _to_xlsx_bytes(lines: List[str]) -> bytes:
    from openpyxl import Workbook
    wb = Workbook()
    ws = wb.active
    ws.title = "Summary"
    ws.append(["Line"])
    for line in lines:
        ws.append([line])
    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue()


def _to_pdf_bytes(lines: List[str], node_label: str) -> bytes:
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.units import cm
    from reportlab.lib.styles import getSampleStyleSheet
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer

    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4, topMargin=2 * cm, bottomMargin=2 * cm)
    styles = getSampleStyleSheet()
    story = [Paragraph(f"Summary Report — {node_label}", styles["Title"]), Spacer(1, 0.5 * cm)]

    for line in lines:
        color = "red" if UNVERIFIED_TAG in line else "black"
        story.append(Paragraph(f'<font color="{color}">{line}</font>', styles["Normal"]))
        story.append(Spacer(1, 0.2 * cm))

    doc.build(story)
    return buf.getvalue()


ReportFormat = ExportFormat  # json | csv | xlsx | pdf | pdf_a — 'csv' renders as plain text lines


async def generate_summary_report(
    db: AsyncSession,
    tenant_id: UUID,
    actor_id: UUID,
    node_id: UUID,
    export_format: ReportFormat,
    mode: ExportMode = "general_export",
) -> Tuple[bytes, str, str]:
    if actor_id is None:
        raise ValueError("report generation requires an actor")

    data = await gather_evidence_package(db, tenant_id, node_id, mode)
    lines = _build_summary_lines(data)

    if export_format == "json":
        content = _to_json_bytes(lines, data)
    elif export_format == "csv":
        content = _to_text_bytes(lines)
    elif export_format == "xlsx":
        content = _to_xlsx_bytes(lines)
    elif export_format in ("pdf", "pdf_a"):
        content = _to_pdf_bytes(lines, data["node"]["label"])
    else:
        raise ValueError(f"Unknown report format '{export_format}'")

    content_hash = hashlib.sha256(content).hexdigest()
    filename = f"summary_report_{node_id}.{export_format.replace('_', '')}" if export_format != "pdf_a" else f"summary_report_{node_id}_pdfa.pdf"
    unverified_count = sum(1 for line in lines if UNVERIFIED_TAG in line)

    await log_action(
        db, actor_id, tenant_id, "evidence.summary_report",
        resource_type="entity_node", resource_id=node_id,
        details={
            "format": export_format,
            "mode": mode,
            "content_sha256": content_hash,
            "content_bytes": len(content),
            "unverified_line_count": unverified_count,
            "total_line_count": len(lines),
        },
    )
    await db.commit()

    return content, filename, CONTENT_TYPES[export_format]
