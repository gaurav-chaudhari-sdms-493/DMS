"""TS3 — proves the VLM archive actually short-circuits a repeat call
through the real wired pipeline, not just the cache service in isolation."""
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


SCHEMA = [{"name": "owner_name", "type": "text"}]


def _one_page_pdf_bytes() -> bytes:
    """Built once per test and reused across both calls in that test --
    reportlab embeds a /CreationDate timestamp, so two SEPARATE calls
    would produce different bytes (and therefore different content
    hashes) even with identical visible content."""
    import io
    from reportlab.pdfgen import canvas
    from reportlab.lib.pagesizes import A4
    buf = io.BytesIO()
    c = canvas.Canvas(buf, pagesize=A4)
    c.drawString(72, 720, "Register page")
    c.showPage()
    c.save()
    return buf.getvalue()


async def _make_doc(db):
    tenant_id = uuid.uuid4()
    tenant = Tenant(id=tenant_id, name=f"TS3 Tenant {uuid.uuid4().hex[:6]}")
    user = User(id=uuid.uuid4(), tenant_id=tenant_id, email=f"ts3_{uuid.uuid4().hex[:6]}@test.com", hashed_password="pw")
    db.add_all([tenant, user])
    await db.flush()
    doc = Document(id=uuid.uuid4(), tenant_id=tenant_id, title="ts3.pdf", status="indexed")
    version = DocumentVersion(
        id=uuid.uuid4(), document_id=doc.id, version_number=1, s3_path="x",
        file_hash=uuid.uuid4().hex, file_size_bytes=1, original_filename="ts3.pdf",
    )
    db.add_all([doc, version])
    await db.flush()
    doc.current_version_id = version.id
    await db.flush()
    return tenant_id, doc.id, version.id


@pytest.mark.asyncio
async def test_second_ingestion_of_same_page_reuses_cached_vlm_response(monkeypatch):
    import app.pipeline.vlm_extraction as vlm_mod
    pdf_bytes = _one_page_pdf_bytes()

    async with AsyncSessionLocal() as db:
        try:
            tenant_id, doc_id, version_id = await _make_doc(db)
            template = FakeTemplate(SCHEMA)

            first_vlm = AsyncMock()
            first_vlm.extract_structured.return_value = json.dumps({
                "rows": [{"owner_name": {"value": "Priya Sharma", "bbox": [0.1, 0.1, 0.5, 0.2], "confidence": 0.9}}],
                "marginalia": [],
            })
            monkeypatch.setattr(vlm_mod, "get_vlm_provider", lambda: first_vlm)

            written_1 = await extract_facts_for_document(
                db, tenant_id, doc_id, version_id, pdf_bytes, "ts3.pdf", pages_text=[{}], template=template,
            )
            await db.commit()
            assert written_1 == 1
            assert first_vlm.extract_structured.call_count == 1

            # Fresh document, fresh VLM mock with a DIFFERENT (wrong-if-called)
            # response -- if the cache didn't work, this document would get
            # "Someone Else" instead of the real cached "Priya Sharma".
            tenant_id_2, doc_id_2, version_id_2 = await _make_doc(db)
            second_vlm = AsyncMock()
            second_vlm.extract_structured.return_value = json.dumps({
                "rows": [{"owner_name": {"value": "Someone Else", "bbox": [0.1, 0.1, 0.5, 0.2], "confidence": 0.9}}],
                "marginalia": [],
            })
            monkeypatch.setattr(vlm_mod, "get_vlm_provider", lambda: second_vlm)

            written_2 = await extract_facts_for_document(
                db, tenant_id_2, doc_id_2, version_id_2, pdf_bytes, "ts3.pdf", pages_text=[{}], template=template,
            )
            await db.commit()

            assert written_2 == 1
            assert second_vlm.extract_structured.call_count == 0  # cache hit -- never called

            res = await db.execute(select(Fact).where(Fact.document_id == doc_id_2, Fact.field_name == "owner_name"))
            fact = res.scalar_one()
            assert fact.value["v"] == "Priya Sharma"  # the cached (first) response, not "Someone Else"
        finally:
            await db.rollback()
            await db.close()


@pytest.mark.asyncio
async def test_different_template_schema_does_not_reuse_cache(monkeypatch):
    """A different field_schema produces a different prompt -- must NOT
    hit the first run's cache entry."""
    import app.pipeline.vlm_extraction as vlm_mod
    pdf_bytes = _one_page_pdf_bytes()

    async with AsyncSessionLocal() as db:
        try:
            tenant_id, doc_id, version_id = await _make_doc(db)
            template_a = FakeTemplate([{"name": "owner_name", "type": "text"}])

            vlm_a = AsyncMock()
            vlm_a.extract_structured.return_value = json.dumps({
                "rows": [{"owner_name": {"value": "Priya Sharma", "bbox": [0.1, 0.1, 0.5, 0.2], "confidence": 0.9}}],
                "marginalia": [],
            })
            monkeypatch.setattr(vlm_mod, "get_vlm_provider", lambda: vlm_a)
            await extract_facts_for_document(db, tenant_id, doc_id, version_id, pdf_bytes, "ts3.pdf", pages_text=[{}], template=template_a)
            await db.commit()
            assert vlm_a.extract_structured.call_count == 1

            tenant_id_2, doc_id_2, version_id_2 = await _make_doc(db)
            template_b = FakeTemplate([{"name": "valuation", "type": "text"}])  # different schema -> different prompt
            vlm_b = AsyncMock()
            vlm_b.extract_structured.return_value = json.dumps({
                "rows": [{"valuation": {"value": "1000", "bbox": [0.1, 0.1, 0.5, 0.2], "confidence": 0.9}}],
                "marginalia": [],
            })
            monkeypatch.setattr(vlm_mod, "get_vlm_provider", lambda: vlm_b)
            await extract_facts_for_document(db, tenant_id_2, doc_id_2, version_id_2, pdf_bytes, "ts3.pdf", pages_text=[{}], template=template_b)
            await db.commit()

            assert vlm_b.extract_structured.call_count == 1  # NOT cached -- genuinely called
        finally:
            await db.rollback()
            await db.close()
