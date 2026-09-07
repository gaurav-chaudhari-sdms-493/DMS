"""role: page_header — live bug, 2026-09-04 (Maharashtra 7/12 template):
village/taluka/district are printed ONCE in a form's header area, never
inside the row table, but field_schema had no way to say that. The VLM
was asked for them per-row like an ordinary column, so it filled them
with the nearest table cell instead (a serial number, a column
abbreviation) rather than the real header text a few lines above --
confirmed live via the raw Chandra OCR text, which DID read the correct
"गाव आपटी / ता. मावळ / जि. पुणे" header line; only the VLM's
per-row-forced structured extraction lost it.

These tests prove page_header fields are written from the top-level
"page_header" object the model returns, not from any row, and that a
page_header key omitted entirely (the prompt's own instruction for "not
visible on this page") is silently skipped rather than guessed."""
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


SCHEMA = [
    {"name": "village", "type": "string", "required": True, "role": "page_header"},
    {"name": "taluka", "type": "string", "required": False, "role": "page_header"},
    {"name": "survey_no", "type": "string", "required": True, "role": "serial"},
    {"name": "owner_name", "type": "string", "required": False},
]


def _one_page_pdf_bytes(seed: str = "") -> bytes:
    import io
    from reportlab.pdfgen import canvas
    from reportlab.lib.pagesizes import A4
    buf = io.BytesIO()
    c = canvas.Canvas(buf, pagesize=A4)
    c.drawString(72, 720, f"Register page {seed}")
    c.showPage()
    c.save()
    return buf.getvalue()


async def _make_doc(db):
    tenant_id = uuid.uuid4()
    tenant = Tenant(id=tenant_id, name=f"PageHeader Tenant {uuid.uuid4().hex[:6]}")
    user = User(id=uuid.uuid4(), tenant_id=tenant_id, email=f"pageheader_{uuid.uuid4().hex[:6]}@test.com", hashed_password="pw")
    db.add_all([tenant, user])
    await db.flush()
    doc = Document(id=uuid.uuid4(), tenant_id=tenant_id, title="7-12.pdf", status="indexed")
    version = DocumentVersion(
        id=uuid.uuid4(), document_id=doc.id, version_number=1, s3_path="x",
        file_hash=uuid.uuid4().hex, file_size_bytes=1, original_filename="7-12.pdf",
    )
    db.add_all([doc, version])
    await db.flush()
    doc.current_version_id = version.id
    await db.flush()
    return tenant_id, doc.id, version.id


@pytest.mark.asyncio
async def test_page_header_field_written_from_header_object_not_row(monkeypatch):
    import app.pipeline.vlm_extraction as vlm_mod
    pdf_bytes = _one_page_pdf_bytes("header-basic")

    async with AsyncSessionLocal() as db:
        try:
            tenant_id, doc_id, version_id = await _make_doc(db)
            template = FakeTemplate(SCHEMA)

            vlm = AsyncMock()
            vlm.extract_structured.return_value = json.dumps({
                "rows": [{
                    "survey_no": {"value": "175", "bbox": [0.1, 0.3, 0.2, 0.35], "confidence": 0.9},
                    "owner_name": {"value": "Ramrao Patil", "bbox": [0.3, 0.3, 0.6, 0.35], "confidence": 0.9},
                }],
                "page_header": {
                    "village": {"value": "Apti", "bbox": [0.1, 0.02, 0.3, 0.06], "confidence": 0.95, "is_handwritten": False},
                    "taluka": {"value": "Maval", "bbox": [0.35, 0.02, 0.5, 0.06], "confidence": 0.9, "is_handwritten": False},
                },
                "marginalia": [],
            })
            monkeypatch.setattr(vlm_mod, "get_vlm_provider", lambda: vlm)

            written = await extract_facts_for_document(
                db, tenant_id, doc_id, version_id, pdf_bytes, "7-12.pdf", pages_text=[{}], template=template,
            )
            await db.commit()

            assert written == 4  # village, taluka, survey_no, owner_name

            res = await db.execute(select(Fact).where(Fact.document_id == doc_id, Fact.field_name == "village"))
            village_fact = res.scalar_one()
            assert village_fact.value["v"] == "Apti"

            res = await db.execute(select(Fact).where(Fact.document_id == doc_id, Fact.field_name == "taluka"))
            assert res.scalar_one().value["v"] == "Maval"

            # survey_no must still be the real row value ("175"), not a
            # header-scoped guess and not skipped because it shares a page
            # with page_header fields.
            res = await db.execute(select(Fact).where(Fact.document_id == doc_id, Fact.field_name == "survey_no"))
            assert res.scalar_one().value["v"] == "175"
        finally:
            await db.rollback()
            await db.close()


@pytest.mark.asyncio
async def test_page_header_field_omitted_when_not_reported(monkeypatch):
    """The prompt tells the model to omit a page_header key entirely when
    it's genuinely not visible (e.g. a continuation page) rather than
    guess -- that omission must produce no Fact at all, not a garbage one."""
    import app.pipeline.vlm_extraction as vlm_mod
    pdf_bytes = _one_page_pdf_bytes("header-omitted")

    async with AsyncSessionLocal() as db:
        try:
            tenant_id, doc_id, version_id = await _make_doc(db)
            template = FakeTemplate(SCHEMA)

            vlm = AsyncMock()
            vlm.extract_structured.return_value = json.dumps({
                "rows": [{"survey_no": {"value": "9", "bbox": [0.1, 0.3, 0.2, 0.35], "confidence": 0.9}}],
                "page_header": {},
                "marginalia": [],
            })
            monkeypatch.setattr(vlm_mod, "get_vlm_provider", lambda: vlm)

            written = await extract_facts_for_document(
                db, tenant_id, doc_id, version_id, pdf_bytes, "7-12.pdf", pages_text=[{}], template=template,
            )
            await db.commit()

            assert written == 1  # only survey_no
            res = await db.execute(select(Fact).where(Fact.document_id == doc_id, Fact.field_name == "village"))
            assert res.scalar_one_or_none() is None
        finally:
            await db.rollback()
            await db.close()
