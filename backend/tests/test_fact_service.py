"""get_facts_for_document -- had zero test coverage before this, same as
the endpoint it backs (found live 2026-09-04 while checking why nothing
in the UI ever showed whether a document's extraction actually stitched
anything: there was no endpoint to ask that question at all)."""
import uuid

import pytest

from app.database import AsyncSessionLocal
from app.models.tenant import Tenant
from app.models.user import User
from app.models.document import Document
from app.models.document_version import DocumentVersion
from app.models.page import DocumentPage
from app.models.fact import Fact
from app.models.fact_region import FactRegion
from app.models.template import Template
from app.services.fact_service import get_facts_for_document, get_table_view_for_document


async def _make_doc(db, tenant_id):
    doc = Document(id=uuid.uuid4(), tenant_id=tenant_id, title="Test Register", status="indexed")
    version = DocumentVersion(
        id=uuid.uuid4(), document_id=doc.id, version_number=1, s3_path="x",
        file_hash=uuid.uuid4().hex, file_size_bytes=1, original_filename="reg.pdf",
    )
    db.add_all([doc, version])
    await db.flush()
    doc.current_version_id = version.id
    await db.flush()
    return doc, version


@pytest.mark.asyncio
async def test_get_facts_for_document_flags_stitched_and_in_review_facts():
    async with AsyncSessionLocal() as db:
        try:
            tenant_id = uuid.uuid4()
            tenant = Tenant(id=tenant_id, name=f"FactSvc Tenant {uuid.uuid4().hex[:6]}")
            user = User(id=uuid.uuid4(), tenant_id=tenant_id, email=f"factsvc_{uuid.uuid4().hex[:6]}@test.com", hashed_password="pw")
            db.add_all([tenant, user])
            await db.commit()

            doc, version = await _make_doc(db, tenant_id)
            page1 = DocumentPage(id=uuid.uuid4(), tenant_id=tenant_id, document_id=doc.id, version_id=version.id, page_number=1, width=800, height=600)
            page2 = DocumentPage(id=uuid.uuid4(), tenant_id=tenant_id, document_id=doc.id, version_id=version.id, page_number=2, width=800, height=600)
            db.add_all([page1, page2])
            await db.flush()

            # A single-page fact -- not stitched.
            single_page_fact = Fact(
                id=uuid.uuid4(), tenant_id=tenant_id, document_id=doc.id, version_id=version.id,
                field_name="owner_name", value={"v": "Priya Sharma"}, confidence=0.9, status="machine",
            )
            db.add(single_page_fact)
            await db.flush()
            db.add(FactRegion(id=uuid.uuid4(), tenant_id=tenant_id, fact_id=single_page_fact.id, page_id=page1.id, x0=0.1, y0=0.1, x1=0.5, y1=0.2))

            # A fact whose regions span both pages -- proof TS1 merged a
            # continuation row from page 2 into this entry.
            stitched_fact = Fact(
                id=uuid.uuid4(), tenant_id=tenant_id, document_id=doc.id, version_id=version.id,
                field_name="description", value={"v": "Land parcel near river continues here"},
                confidence=0.85, status="machine",
            )
            db.add(stitched_fact)
            await db.flush()
            db.add(FactRegion(id=uuid.uuid4(), tenant_id=tenant_id, fact_id=stitched_fact.id, page_id=page1.id, x0=0.1, y0=0.3, x1=0.9, y1=0.35))
            db.add(FactRegion(id=uuid.uuid4(), tenant_id=tenant_id, fact_id=stitched_fact.id, page_id=page2.id, x0=0.1, y0=0.1, x1=0.9, y1=0.15))

            # A _stitch_ambiguous sentinel -- in review, not stitched.
            ambiguous_fact = Fact(
                id=uuid.uuid4(), tenant_id=tenant_id, document_id=doc.id, version_id=version.id,
                field_name="_stitch_ambiguous", value={"reason": "unclear"}, status="in_review",
            )
            db.add(ambiguous_fact)
            await db.flush()
            db.add(FactRegion(id=uuid.uuid4(), tenant_id=tenant_id, fact_id=ambiguous_fact.id, page_id=page1.id, x0=0.0, y0=0.0, x1=1.0, y1=1.0))
            await db.commit()

            result = await get_facts_for_document(db, doc.id, tenant_id)

            by_name = {f["field_name"]: f for f in result["facts"]}
            assert by_name["owner_name"]["stitched"] is False
            assert by_name["owner_name"]["page_numbers"] == [1]

            assert by_name["description"]["stitched"] is True
            assert by_name["description"]["page_numbers"] == [1, 2]

            assert by_name["_stitch_ambiguous"]["status"] == "in_review"
            assert by_name["_stitch_ambiguous"]["stitched"] is False

            assert result["stitched_field_count"] == 1
            assert result["in_review_count"] == 1
            assert result["document_id"] == str(doc.id)

            # Live bug, 2026-09-04: on a real document with hundreds of
            # facts, the few stitched/in_review ones sorted by plain
            # field_name were buried at random scroll positions among
            # hundreds of identical-looking machine-status rows -- a
            # working stitch looked indistinguishable from nothing
            # happening. in_review must sort first, then stitched, then
            # everything else -- never just alphabetical.
            names_in_order = [f["field_name"] for f in result["facts"]]
            assert names_in_order[0] == "_stitch_ambiguous"  # the only in_review fact
            assert names_in_order[1] == "description"  # the only stitched fact
            assert names_in_order[2] == "owner_name"  # neither -- comes last
        finally:
            await db.rollback()
            await db.close()


@pytest.mark.asyncio
async def test_get_facts_for_document_wrong_tenant_raises_404():
    from fastapi import HTTPException

    async with AsyncSessionLocal() as db:
        try:
            tenant_id = uuid.uuid4()
            other_tenant_id = uuid.uuid4()
            tenant = Tenant(id=tenant_id, name=f"FactSvc404 Tenant {uuid.uuid4().hex[:6]}")
            db.add(tenant)
            await db.commit()

            doc, _ = await _make_doc(db, tenant_id)
            await db.commit()

            with pytest.raises(HTTPException) as exc_info:
                await get_facts_for_document(db, doc.id, other_tenant_id)
            assert exc_info.value.status_code == 404
        finally:
            await db.rollback()
            await db.close()


@pytest.mark.asyncio
async def test_get_table_view_reconstructs_rows_by_vertical_position():
    """Live feature, 2026-09-04: no row identifier is ever stored on a
    Fact -- rows are reconstructed purely from FactRegion's existing
    (page, y0), since fields from the same original table row land at
    (nearly) the same vertical position. Two rows close together on the
    same page must still separate into two rows, not merge into one."""
    async with AsyncSessionLocal() as db:
        try:
            tenant_id = uuid.uuid4()
            tenant = Tenant(id=tenant_id, name=f"TableView Tenant {uuid.uuid4().hex[:6]}")
            db.add(tenant)
            await db.commit()

            template = Template(
                id=uuid.uuid4(), form_type=f"Table View Test Form {uuid.uuid4().hex[:6]}", era_label="test",
                layout="single_page",
                field_schema=[
                    {"name": "village", "type": "string", "role": "page_header"},
                    {"name": "sr_no", "type": "string", "role": "serial"},
                    {"name": "name", "type": "string"},
                    {"name": "amount", "type": "string"},
                ],
            )
            db.add(template)
            await db.flush()

            doc, version = await _make_doc(db, tenant_id)
            doc.matched_template_id = template.id
            page1 = DocumentPage(id=uuid.uuid4(), tenant_id=tenant_id, document_id=doc.id, version_id=version.id, page_number=1, width=800, height=600)
            db.add(page1)
            await db.flush()

            def add_fact(field_name, value, y0, y1=None):
                f = Fact(
                    id=uuid.uuid4(), tenant_id=tenant_id, document_id=doc.id, version_id=version.id,
                    field_name=field_name, value={"v": value}, confidence=0.9, status="machine",
                )
                db.add(f)
                return f

            async def flush_region(fact, y0, y1=None):
                await db.flush()
                db.add(FactRegion(id=uuid.uuid4(), tenant_id=tenant_id, fact_id=fact.id, page_id=page1.id, x0=0.1, y0=y0, x1=0.5, y1=y1 or y0 + 0.02))

            village_fact = add_fact("village", "Apti", 0.05)
            await flush_region(village_fact, 0.05)

            row1_sr = add_fact("sr_no", "1", 0.30)
            await flush_region(row1_sr, 0.30)
            row1_name = add_fact("name", "Ramrao Patil", 0.305)  # same row, tiny jitter
            await flush_region(row1_name, 0.305)

            row2_sr = add_fact("sr_no", "2", 0.45)  # a different row, well past tolerance
            await flush_region(row2_sr, 0.45)
            row2_amount = add_fact("amount", "500", 0.452)
            await flush_region(row2_amount, 0.452)

            await db.commit()

            result = await get_table_view_for_document(db, doc.id, tenant_id)

            assert result["page_header"] == {"village": "Apti"}
            assert result["columns"] == ["sr_no", "name", "amount"]
            assert result["row_count"] == 2
            assert result["rows"][0]["values"] == {"sr_no": "1", "name": "Ramrao Patil"}
            assert result["rows"][1]["values"] == {"sr_no": "2", "amount": "500"}
            assert result["rows"][0]["needs_review"] is False
            assert result["rows"][1]["needs_review"] is False
        finally:
            await db.rollback()
            await db.close()


@pytest.mark.asyncio
async def test_get_table_view_flags_a_row_needing_review():
    """A row where the T22 row-coverage gate forced every field to
    in_review must surface that in the reconstructed table too, not just
    in the flat facts list -- otherwise a mis-mapped row (e.g. a cover
    page's content forced into the row schema) looks identical to a
    normal one in the table a reviewer is actually looking at."""
    async with AsyncSessionLocal() as db:
        try:
            tenant_id = uuid.uuid4()
            tenant = Tenant(id=tenant_id, name=f"TableViewReview Tenant {uuid.uuid4().hex[:6]}")
            db.add(tenant)
            await db.commit()

            template = Template(
                id=uuid.uuid4(), form_type=f"Table View Review Test Form {uuid.uuid4().hex[:6]}", era_label="test",
                layout="single_page",
                field_schema=[{"name": "sr_no", "type": "string", "role": "serial"}, {"name": "name", "type": "string"}],
            )
            db.add(template)
            await db.flush()

            doc, version = await _make_doc(db, tenant_id)
            doc.matched_template_id = template.id
            page1 = DocumentPage(id=uuid.uuid4(), tenant_id=tenant_id, document_id=doc.id, version_id=version.id, page_number=1, width=800, height=600)
            db.add(page1)
            await db.flush()

            fact = Fact(
                id=uuid.uuid4(), tenant_id=tenant_id, document_id=doc.id, version_id=version.id,
                field_name="sr_no", value={"v": "garbled cover text"}, confidence=0.9, status="in_review",
            )
            db.add(fact)
            await db.flush()
            db.add(FactRegion(id=uuid.uuid4(), tenant_id=tenant_id, fact_id=fact.id, page_id=page1.id, x0=0.1, y0=0.1, x1=0.5, y1=0.12))
            await db.commit()

            result = await get_table_view_for_document(db, doc.id, tenant_id)

            assert result["row_count"] == 1
            assert result["rows"][0]["needs_review"] is True
        finally:
            await db.rollback()
            await db.close()


@pytest.mark.asyncio
async def test_get_table_view_marks_a_row_stitched_when_any_field_spans_pages():
    async with AsyncSessionLocal() as db:
        try:
            tenant_id = uuid.uuid4()
            tenant = Tenant(id=tenant_id, name=f"TableViewStitch Tenant {uuid.uuid4().hex[:6]}")
            db.add(tenant)
            await db.commit()

            template = Template(
                id=uuid.uuid4(), form_type=f"Table View Stitch Test Form {uuid.uuid4().hex[:6]}", era_label="test",
                layout="single_page",
                field_schema=[{"name": "sr_no", "type": "string", "role": "serial"}, {"name": "description", "type": "string"}],
            )
            db.add(template)
            await db.flush()

            doc, version = await _make_doc(db, tenant_id)
            doc.matched_template_id = template.id
            page1 = DocumentPage(id=uuid.uuid4(), tenant_id=tenant_id, document_id=doc.id, version_id=version.id, page_number=1, width=800, height=600)
            page2 = DocumentPage(id=uuid.uuid4(), tenant_id=tenant_id, document_id=doc.id, version_id=version.id, page_number=2, width=800, height=600)
            db.add_all([page1, page2])
            await db.flush()

            sr_fact = Fact(
                id=uuid.uuid4(), tenant_id=tenant_id, document_id=doc.id, version_id=version.id,
                field_name="sr_no", value={"v": "5"}, confidence=0.9, status="machine",
            )
            db.add(sr_fact)
            await db.flush()
            db.add(FactRegion(id=uuid.uuid4(), tenant_id=tenant_id, fact_id=sr_fact.id, page_id=page1.id, x0=0.1, y0=0.9, x1=0.5, y1=0.92))

            desc_fact = Fact(
                id=uuid.uuid4(), tenant_id=tenant_id, document_id=doc.id, version_id=version.id,
                field_name="description", value={"v": "continues onto next page"}, confidence=0.9, status="machine",
            )
            db.add(desc_fact)
            await db.flush()
            db.add(FactRegion(id=uuid.uuid4(), tenant_id=tenant_id, fact_id=desc_fact.id, page_id=page1.id, x0=0.1, y0=0.9, x1=0.9, y1=0.95))
            db.add(FactRegion(id=uuid.uuid4(), tenant_id=tenant_id, fact_id=desc_fact.id, page_id=page2.id, x0=0.1, y0=0.05, x1=0.9, y1=0.1))
            await db.commit()

            result = await get_table_view_for_document(db, doc.id, tenant_id)

            assert result["row_count"] == 1
            assert result["rows"][0]["stitched"] is True
            assert result["rows"][0]["page_number"] == 1  # anchored to the EARLIEST page, not where it continued
        finally:
            await db.rollback()
            await db.close()
