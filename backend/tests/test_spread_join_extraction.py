import io
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
from app.pipeline.vlm_extraction import _extract_spread_facts
from sqlalchemy import select


def _two_page_pdf_bytes() -> bytes:
    from reportlab.pdfgen import canvas
    from reportlab.lib.pagesizes import A4

    buf = io.BytesIO()
    c = canvas.Canvas(buf, pagesize=A4)
    c.drawString(72, 720, "Left half — register page")
    c.showPage()
    c.drawString(72, 720, "Right half — register page")
    c.showPage()
    c.save()
    return buf.getvalue()


SPREAD_FIELD_SCHEMA = [
    {"name": "serial_no", "type": "text", "role": "serial"},
    {"name": "owner_name", "type": "text", "half": "left"},
    {"name": "valuation", "type": "text", "half": "right"},
]


def _vlm_json(rows: list) -> str:
    return json.dumps({"rows": rows, "marginalia": []})


async def _make_doc(db):
    tenant_id = uuid.uuid4()
    actor_id = uuid.uuid4()
    tenant = Tenant(id=tenant_id, name=f"Spread Tenant {uuid.uuid4().hex[:6]}")
    user = User(id=actor_id, tenant_id=tenant_id, email=f"spread_{uuid.uuid4().hex[:6]}@test.com", hashed_password="pw")
    db.add_all([tenant, user])
    await db.flush()

    doc = Document(id=uuid.uuid4(), tenant_id=tenant_id, title="spread.pdf", status="indexed")
    version = DocumentVersion(
        id=uuid.uuid4(), tenant_id=tenant_id, document_id=doc.id, version_number=1, s3_path="x",
        file_hash=uuid.uuid4().hex, file_size_bytes=1, original_filename="spread.pdf",
    )
    db.add_all([doc, version])
    await db.flush()
    doc.current_version_id = version.id
    await db.flush()

    return tenant_id, doc.id, version.id


@pytest.mark.asyncio
async def test_spread_extraction_merges_matching_serials_into_facts():
    async with AsyncSessionLocal() as db:
        try:
            tenant_id, doc_id, version_id = await _make_doc(db)

            left_response = _vlm_json([{
                "serial_no": {"value": "1", "bbox": [0.1, 0.1, 0.2, 0.15], "confidence": 0.99},
                "owner_name": {"value": "Priya Sharma", "bbox": [0.3, 0.1, 0.6, 0.15], "confidence": 0.95},
            }])
            right_response = _vlm_json([{
                "serial_no": {"value": "1", "bbox": [0.1, 0.1, 0.2, 0.15], "confidence": 0.99},
                "valuation": {"value": "1000", "bbox": [0.3, 0.1, 0.6, 0.15], "confidence": 0.9},
            }])
            fake_vlm = AsyncMock()
            fake_vlm.extract_structured.side_effect = [left_response, right_response]

            written = await _extract_spread_facts(
                db, tenant_id, doc_id, version_id, _two_page_pdf_bytes(), "pdf",
                fake_vlm, SPREAD_FIELD_SCHEMA, max_pages=2,
            )
            await db.commit()

            assert written == 2
            res = await db.execute(select(Fact).where(Fact.document_id == doc_id))
            facts_by_field = {f.field_name: f for f in res.scalars().all()}
            assert facts_by_field["owner_name"].value == {"v": "Priya Sharma"}
            assert facts_by_field["owner_name"].status == "machine"
            assert facts_by_field["valuation"].value == {"v": "1000"}
            assert "_join_mismatch" not in facts_by_field
        finally:
            await db.rollback()
            await db.close()


@pytest.mark.asyncio
async def test_spread_extraction_writes_join_mismatch_fact_on_serial_disagreement():
    async with AsyncSessionLocal() as db:
        try:
            tenant_id, doc_id, version_id = await _make_doc(db)

            left_response = _vlm_json([{
                "serial_no": {"value": "1", "bbox": [0.1, 0.1, 0.2, 0.15], "confidence": 0.99},
                "owner_name": {"value": "Priya Sharma", "bbox": [0.3, 0.1, 0.6, 0.15], "confidence": 0.95},
            }])
            right_response = _vlm_json([{
                "serial_no": {"value": "2", "bbox": [0.1, 0.1, 0.2, 0.15], "confidence": 0.99},
                "valuation": {"value": "1000", "bbox": [0.3, 0.1, 0.6, 0.15], "confidence": 0.9},
            }])
            fake_vlm = AsyncMock()
            fake_vlm.extract_structured.side_effect = [left_response, right_response]

            written = await _extract_spread_facts(
                db, tenant_id, doc_id, version_id, _two_page_pdf_bytes(), "pdf",
                fake_vlm, SPREAD_FIELD_SCHEMA, max_pages=2,
            )
            await db.commit()

            assert written == 1
            res = await db.execute(select(Fact).where(Fact.document_id == doc_id, Fact.field_name == "_join_mismatch"))
            mismatch = res.scalar_one()
            assert mismatch.status == "in_review"
            assert mismatch.value["left_page"] == 1
            assert mismatch.value["right_page"] == 2
            assert "1" in mismatch.value["reason"] or "2" in mismatch.value["reason"]
        finally:
            await db.rollback()
            await db.close()
