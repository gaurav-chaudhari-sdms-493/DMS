"""TS5 — real end-to-end proof that ditto verbatim/was_ditto_filled/
unresolved handling is actually wired into extract_facts_for_document,
not just unit-tested on the handler in isolation (test_handlers.py)."""
import json
import uuid

import pytest
from unittest.mock import AsyncMock

from app.database import AsyncSessionLocal
from app.models.tenant import Tenant
from app.models.user import User
from app.models.document import Document
from app.models.document_version import DocumentVersion
from app.models.fact import Fact
from app.pipeline.vlm_extraction import extract_facts_for_document
from sqlalchemy import select


class FakeTemplate:
    def __init__(self, field_schema, layout="single"):
        self.field_schema = field_schema
        self.layout = layout


def _f(value, bbox=None, confidence=0.95):
    d = {"value": value, "confidence": confidence}
    if bbox:
        d["bbox"] = bbox
    return d


def _vlm_json(rows):
    return json.dumps({"rows": rows, "marginalia": []})


def _one_page_pdf_bytes():
    import io
    from reportlab.pdfgen import canvas
    from reportlab.lib.pagesizes import A4
    buf = io.BytesIO()
    c = canvas.Canvas(buf, pagesize=A4)
    c.drawString(72, 720, "Gazette table")
    c.showPage()
    c.save()
    return buf.getvalue()


async def _make_doc(db, title="ts5.pdf"):
    tenant_id = uuid.uuid4()
    tenant = Tenant(id=tenant_id, name=f"TS5 Tenant {uuid.uuid4().hex[:6]}")
    user = User(id=uuid.uuid4(), tenant_id=tenant_id, email=f"ts5_{uuid.uuid4().hex[:6]}@test.com", hashed_password="pw")
    db.add_all([tenant, user])
    await db.flush()
    doc = Document(id=uuid.uuid4(), tenant_id=tenant_id, title=title, status="indexed")
    version = DocumentVersion(
        id=uuid.uuid4(), document_id=doc.id, version_number=1, s3_path="x",
        file_hash=uuid.uuid4().hex, file_size_bytes=1, original_filename=title,
    )
    db.add_all([doc, version])
    await db.flush()
    doc.current_version_id = version.id
    await db.flush()
    return tenant_id, doc.id, version.id


DITTO_SCHEMA = [
    {"name": "serial_no", "type": "text", "role": "serial"},
    {"name": "shia_or_sunni", "type": "text", "ditto_eligible": True},
]


@pytest.mark.asyncio
async def test_real_do_mark_resolves_with_verbatim_preserved(monkeypatch):
    """Mirrors the actual real 1973 Maharashtra Waqf Board gazette
    table's own convention (rows 180-197: "Sunni" then "Do." repeatedly)."""
    import app.pipeline.vlm_extraction as vlm_mod

    async with AsyncSessionLocal() as db:
        try:
            tenant_id, doc_id, version_id = await _make_doc(db)
            fake_vlm = AsyncMock()
            fake_vlm.extract_structured.return_value = _vlm_json([
                {"serial_no": _f("180", bbox=[0.1, 0.10, 0.2, 0.15]), "shia_or_sunni": _f("Sunni", bbox=[0.3, 0.10, 0.5, 0.15])},
                {"serial_no": _f("181", bbox=[0.1, 0.20, 0.2, 0.25]), "shia_or_sunni": _f("Do.", bbox=[0.3, 0.20, 0.5, 0.25])},
            ])
            monkeypatch.setattr(vlm_mod, "get_vlm_provider", lambda: fake_vlm)

            template = FakeTemplate(DITTO_SCHEMA)
            await extract_facts_for_document(
                db, tenant_id, doc_id, version_id, _one_page_pdf_bytes(), "ts5.pdf", pages_text=[{}], template=template,
            )
            await db.commit()

            res = await db.execute(select(Fact).where(Fact.document_id == doc_id, Fact.field_name == "shia_or_sunni"))
            facts = res.scalars().all()
            assert len(facts) == 2

            original_fact = next(f for f in facts if "verbatim" not in f.value)
            assert original_fact.value["v"] == "Sunni"

            ditto_fact = next(f for f in facts if "verbatim" in f.value)
            assert ditto_fact.value["v"] == "Sunni"  # resolved
            assert ditto_fact.value["verbatim"] == "Do."  # literal reading preserved
            assert ditto_fact.value["was_ditto_filled"] is True
            assert ditto_fact.status == "machine"  # resolved cleanly -- normal confidence banding applies
        finally:
            await db.rollback()
            await db.close()


@pytest.mark.asyncio
async def test_unresolved_ditto_forces_in_review_status(monkeypatch):
    """A ditto mark with nothing valid above it must never be silently
    guessed -- forced to in_review regardless of confidence banding."""
    import app.pipeline.vlm_extraction as vlm_mod

    async with AsyncSessionLocal() as db:
        try:
            tenant_id, doc_id, version_id = await _make_doc(db)
            fake_vlm = AsyncMock()
            # First row's ditto-eligible field has nothing above to copy.
            fake_vlm.extract_structured.return_value = _vlm_json([
                {"serial_no": _f("1", bbox=[0.1, 0.10, 0.2, 0.15]), "shia_or_sunni": _f("Do.", bbox=[0.3, 0.10, 0.5, 0.15], confidence=0.99)},
            ])
            monkeypatch.setattr(vlm_mod, "get_vlm_provider", lambda: fake_vlm)

            template = FakeTemplate(DITTO_SCHEMA)
            await extract_facts_for_document(
                db, tenant_id, doc_id, version_id, _one_page_pdf_bytes(), "ts5.pdf", pages_text=[{}], template=template,
            )
            await db.commit()

            res = await db.execute(select(Fact).where(Fact.document_id == doc_id, Fact.field_name == "shia_or_sunni"))
            fact = res.scalar_one()
            assert fact.status == "in_review"  # forced, despite confidence=0.99
            assert fact.value["ditto_unresolved"] is True
            assert fact.value["verbatim"] == "Do."
        finally:
            await db.rollback()
            await db.close()


CHAIN_ANCHOR_SCHEMA = [
    {"name": "serial_no", "type": "text", "role": "serial"},
    {"name": "village", "type": "text", "role": "chain_anchor", "ditto_eligible": True},
    {"name": "khatedar", "type": "text", "ditto_eligible": True},
]


@pytest.mark.asyncio
async def test_chain_anchor_resets_other_fields_on_real_village_change(monkeypatch):
    import app.pipeline.vlm_extraction as vlm_mod

    async with AsyncSessionLocal() as db:
        try:
            tenant_id, doc_id, version_id = await _make_doc(db)
            fake_vlm = AsyncMock()
            fake_vlm.extract_structured.return_value = _vlm_json([
                {"serial_no": _f("1", bbox=[0.1, 0.10, 0.2, 0.15]), "village": _f("Basmath", bbox=[0.3, 0.10, 0.5, 0.15]), "khatedar": _f("Ramrao Patil", bbox=[0.5, 0.10, 0.7, 0.15])},
                {"serial_no": _f("2", bbox=[0.1, 0.20, 0.2, 0.25]), "village": _f("Kalamnuri", bbox=[0.3, 0.20, 0.5, 0.25]), "khatedar": _f("Do.", bbox=[0.5, 0.20, 0.7, 0.25], confidence=0.9)},
            ])
            monkeypatch.setattr(vlm_mod, "get_vlm_provider", lambda: fake_vlm)

            template = FakeTemplate(CHAIN_ANCHOR_SCHEMA)
            await extract_facts_for_document(
                db, tenant_id, doc_id, version_id, _one_page_pdf_bytes(), "ts5.pdf", pages_text=[{}], template=template,
            )
            await db.commit()

            res = await db.execute(select(Fact).where(Fact.document_id == doc_id, Fact.field_name == "khatedar"))
            facts = res.scalars().all()
            assert len(facts) == 2
            unresolved_fact = next(f for f in facts if "ditto_unresolved" in f.value)
            assert unresolved_fact.status == "in_review"
            assert unresolved_fact.value["ditto_unresolved"] is True
            assert unresolved_fact.value["verbatim"] == "Do."
        finally:
            await db.rollback()
            await db.close()
