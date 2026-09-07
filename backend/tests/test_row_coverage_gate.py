"""T22 row-coverage gate — live bug, 2026-09-04: Chandra's /convert isn't
instruction-following (chandra_provider.py maps whatever table it detects
onto our field list by column ORDER, blind to whether the page is even
this template's table). Confirmed live: a Wakf gazette's non-tabular
cover page still produced a "row", cramming a legal-notice paragraph into
just 3 of the template's 14 fields -- nowhere near the ~12-14 fields a
genuine row populates. A row whose populated-field fraction falls below
ROW_COVERAGE_REVIEW_THRESHOLD is forced into human review regardless of
its per-field confidence, rather than trusted as ordinary machine data or
silently dropped."""
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
    def __init__(self, field_schema, layout="single_page"):
        self.field_schema = field_schema
        self.layout = layout


# 6 row-level fields -- 2/6 populated (33%) is below the 40% threshold,
# 5/6 (83%) is comfortably above it.
SCHEMA = [
    {"name": "sr_no", "type": "string", "required": False, "role": "serial"},
    {"name": "name", "type": "string", "required": False},
    {"name": "sect", "type": "string", "required": False},
    {"name": "nature", "type": "string", "required": False},
    {"name": "value", "type": "string", "required": False},
    {"name": "income", "type": "string", "required": False},
]


def _f(value, bbox, confidence=0.95):
    return {"value": value, "bbox": bbox, "confidence": confidence, "is_handwritten": False}


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
    tenant = Tenant(id=tenant_id, name=f"RowCoverage Tenant {uuid.uuid4().hex[:6]}")
    user = User(id=uuid.uuid4(), tenant_id=tenant_id, email=f"rowcoverage_{uuid.uuid4().hex[:6]}@test.com", hashed_password="pw")
    db.add_all([tenant, user])
    await db.flush()
    doc = Document(id=uuid.uuid4(), tenant_id=tenant_id, title="cover.pdf", status="indexed")
    version = DocumentVersion(
        id=uuid.uuid4(), document_id=doc.id, version_number=1, s3_path="x",
        file_hash=uuid.uuid4().hex, file_size_bytes=1, original_filename="cover.pdf",
    )
    db.add_all([doc, version])
    await db.flush()
    doc.current_version_id = version.id
    await db.flush()
    return tenant_id, doc.id, version.id


@pytest.mark.asyncio
async def test_low_coverage_row_forced_into_review(monkeypatch):
    import app.pipeline.vlm_extraction as vlm_mod
    pdf_bytes = _one_page_pdf_bytes("low-coverage")

    async with AsyncSessionLocal() as db:
        try:
            tenant_id, doc_id, version_id = await _make_doc(db)
            template = FakeTemplate(SCHEMA)

            # Only 2 of 6 row fields populated -- a cover-page-shaped
            # mis-mapping, not a genuine sparse row.
            vlm = AsyncMock()
            vlm.extract_structured.return_value = json.dumps({
                "rows": [{
                    "sr_no": _f("भाग एक-शासकीय अधिसूचना...", bbox=[0.1, 0.1, 0.5, 0.2]),
                    "name": _f("पृष्ठे ते ४१३०अ", bbox=[0.3, 0.1, 0.6, 0.2]),
                }],
                "marginalia": [],
            })
            monkeypatch.setattr(vlm_mod, "get_vlm_provider", lambda: vlm)

            written = await extract_facts_for_document(
                db, tenant_id, doc_id, version_id, pdf_bytes, "cover.pdf", pages_text=[{}], template=template,
            )
            await db.commit()

            assert written == 2
            res = await db.execute(select(Fact).where(Fact.document_id == doc_id))
            facts = res.scalars().all()
            assert len(facts) == 2
            assert all(f.status == "in_review" for f in facts)
        finally:
            await db.rollback()
            await db.close()


@pytest.mark.asyncio
async def test_high_coverage_row_keeps_normal_confidence_banding(monkeypatch):
    import app.pipeline.vlm_extraction as vlm_mod
    pdf_bytes = _one_page_pdf_bytes("high-coverage")

    async with AsyncSessionLocal() as db:
        try:
            tenant_id, doc_id, version_id = await _make_doc(db)
            template = FakeTemplate(SCHEMA)

            # 5 of 6 row fields populated with high confidence -- a
            # genuine row, must NOT be forced into review by the gate.
            vlm = AsyncMock()
            vlm.extract_structured.return_value = json.dumps({
                "rows": [{
                    "sr_no": _f("WB-15", bbox=[0.1, 0.1, 0.2, 0.15], confidence=0.98),
                    "name": _f("Anjuman Jumma Masjid Trust", bbox=[0.2, 0.1, 0.5, 0.15], confidence=0.97),
                    "sect": _f("SUNNI", bbox=[0.5, 0.1, 0.6, 0.15], confidence=0.99),
                    "nature": _f("Religious", bbox=[0.6, 0.1, 0.7, 0.15], confidence=0.98),
                    "value": _f("Variable", bbox=[0.7, 0.1, 0.8, 0.15], confidence=0.96),
                }],
                "marginalia": [],
            })
            monkeypatch.setattr(vlm_mod, "get_vlm_provider", lambda: vlm)

            written = await extract_facts_for_document(
                db, tenant_id, doc_id, version_id, pdf_bytes, "cover.pdf", pages_text=[{}], template=template,
            )
            await db.commit()

            assert written == 5
            res = await db.execute(select(Fact).where(Fact.document_id == doc_id))
            facts = res.scalars().all()
            assert len(facts) == 5
            # High confidence + good coverage -> the gate must not
            # override normal confidence-banding (machine, not in_review).
            assert all(f.status == "machine" for f in facts)
        finally:
            await db.rollback()
            await db.close()
