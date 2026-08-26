"""TS1 — real, end-to-end proof that the table-stitching engine is
actually wired into the live extraction pipeline, not just unit-tested in
isolation (test_table_stitch.py covers the pure engine). Same AsyncMock
VLM/DB pattern test_spread_join_extraction.py already established for
exercising vlm_extraction.py against a real Postgres DB."""
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
from app.models.fact_region import FactRegion
from app.models.table_shape_decision import TableShapeDecision
from app.pipeline.vlm_extraction import extract_facts_for_document, _extract_spread_facts, _stitch_vertical_segments
from sqlalchemy import select


def _f(value, bbox=None, confidence=0.95, handwritten=False):
    d = {"value": value, "confidence": confidence, "is_handwritten": handwritten}
    if bbox:
        d["bbox"] = bbox
    return d


def _vlm_json(rows: list, marginalia: list = None) -> str:
    return json.dumps({"rows": rows, "marginalia": marginalia or []})


def _n_page_pdf_bytes(n: int) -> bytes:
    from reportlab.pdfgen import canvas
    from reportlab.lib.pagesizes import A4
    buf = io.BytesIO()
    c = canvas.Canvas(buf, pagesize=A4)
    for i in range(n):
        c.drawString(72, 720, f"Page {i + 1}")
        c.showPage()
    c.save()
    return buf.getvalue()


class FakeTemplate:
    def __init__(self, field_schema, layout="single"):
        self.field_schema = field_schema
        self.layout = layout


async def _make_doc(db, title="stitch.pdf"):
    tenant_id = uuid.uuid4()
    actor_id = uuid.uuid4()
    tenant = Tenant(id=tenant_id, name=f"Stitch Tenant {uuid.uuid4().hex[:6]}")
    user = User(id=actor_id, tenant_id=tenant_id, email=f"stitch_{uuid.uuid4().hex[:6]}@test.com", hashed_password="pw")
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


CONTINUATION_SCHEMA = [
    {"name": "serial_no", "type": "text", "role": "serial"},
    {"name": "owner_name", "type": "text"},
    {"name": "description", "type": "text"},
]


@pytest.mark.asyncio
async def test_continuation_row_merges_across_a_page_boundary(monkeypatch):
    """The real bug TS1 fixes: before this, a continuation row starting a
    fresh page raised inside merge_continuation_rows (no prior row in
    THAT page's own list) and silently fell back to being treated as a
    normal, disconnected row — losing the concatenation and orphaning a
    description fact under no serial number at all."""
    import app.pipeline.vlm_extraction as vlm_mod
    async with AsyncSessionLocal() as db:
        try:
            tenant_id, doc_id, version_id = await _make_doc(db)

            page1_response = _vlm_json([{
                "serial_no": _f("5", bbox=[0.1, 0.1, 0.2, 0.15]),
                "owner_name": _f("Priya Sharma", bbox=[0.3, 0.1, 0.6, 0.15]),
                "description": _f("Land parcel near river", bbox=[0.3, 0.15, 0.9, 0.2]),
            }])
            page2_response = _vlm_json([
                {
                    "serial_no": _f("", bbox=[0.1, 0.1, 0.2, 0.15]),
                    "description": _f(" continues here", bbox=[0.3, 0.1, 0.9, 0.15]),
                },
                {
                    "serial_no": _f("6", bbox=[0.1, 0.2, 0.2, 0.25]),
                    "owner_name": _f("Ravi Kumar", bbox=[0.3, 0.2, 0.6, 0.25]),
                    "description": _f("Second entry", bbox=[0.3, 0.25, 0.9, 0.3]),
                },
            ])
            fake_vlm = AsyncMock()
            fake_vlm.extract_structured.side_effect = [page1_response, page2_response]
            monkeypatch.setattr(vlm_mod, "get_vlm_provider", lambda: fake_vlm)

            template = FakeTemplate(CONTINUATION_SCHEMA)
            written = await extract_facts_for_document(
                db, tenant_id, doc_id, version_id, _n_page_pdf_bytes(2), "stitch.pdf",
                pages_text=[{}, {}], template=template,
            )
            await db.commit()

            assert fake_vlm.extract_structured.call_count == 2

            res = await db.execute(select(Fact).where(Fact.document_id == doc_id))
            facts = res.scalars().all()
            descriptions = {f.value["v"] for f in facts if f.field_name == "description"}
            assert "Land parcel near river continues here" in descriptions
            assert "Second entry" in descriptions
            # The continuation row must NOT have produced its own orphan
            # description fact separate from the merged one.
            assert " continues here".strip() not in descriptions

            owners = {f.value["v"] for f in facts if f.field_name == "owner_name"}
            assert owners == {"Priya Sharma", "Ravi Kumar"}

            merged_fact = next(f for f in facts if f.field_name == "description" and f.value["v"].startswith("Land parcel"))
            regions_res = await db.execute(select(FactRegion).where(FactRegion.fact_id == merged_fact.id))
            regions = regions_res.scalars().all()
            assert len(regions) == 2  # spans both physical pages
            assert len({r.page_id for r in regions}) == 2
        finally:
            await db.rollback()
            await db.close()


@pytest.mark.asyncio
async def test_ambiguous_pages_without_adjudication_are_not_stitched(monkeypatch):
    """Regression guard: a page pair whose field-set overlap is genuinely
    ambiguous (not clearly vertical, not clearly horizontal) must NOT be
    silently merged when no adjudicator is available — the safe default
    (see _stitch_vertical_segments docstring) is to leave them separate."""
    import app.pipeline.vlm_extraction as vlm_mod
    async with AsyncSessionLocal() as db:
        try:
            tenant_id, doc_id, version_id = await _make_doc(db)
            page1_response = _vlm_json([{
                "serial_no": _f("1", bbox=[0.1, 0.1, 0.2, 0.15]),
                "owner_name": _f("Priya Sharma", bbox=[0.3, 0.1, 0.6, 0.15]),
                "description": _f("First register page", bbox=[0.3, 0.15, 0.9, 0.2]),
            }])
            # Page 2 only has "description" evidence (owner_name blank/absent)
            # — partial overlap with page 1, neither clearly the same table
            # (similarity 0.5, below threshold) nor clearly a disjoint
            # column-band (they share "description") -> ambiguous.
            page2_response = _vlm_json([{
                "serial_no": _f("101", bbox=[0.1, 0.1, 0.2, 0.15]),
                "description": _f("Different register entirely", bbox=[0.3, 0.15, 0.9, 0.2]),
            }])
            fake_vlm = AsyncMock()
            fake_vlm.extract_structured.side_effect = [page1_response, page2_response]
            monkeypatch.setattr(vlm_mod, "get_vlm_provider", lambda: fake_vlm)

            def _no_local_llm():
                raise RuntimeError("no local LLM provider configured")
            monkeypatch.setattr(vlm_mod, "get_llm_provider", _no_local_llm)

            template = FakeTemplate(CONTINUATION_SCHEMA)
            written = await extract_facts_for_document(
                db, tenant_id, doc_id, version_id, _n_page_pdf_bytes(2), "unrelated.pdf",
                pages_text=[{}, {}], template=template,
            )
            await db.commit()

            res = await db.execute(select(Fact).where(Fact.document_id == doc_id, Fact.field_name == "description"))
            values = {f.value["v"] for f in res.scalars().all()}
            # Unchanged, unmerged — proves the two pages stayed separate
            # segments rather than being concatenated by merge_continuation_rows.
            assert values == {"First register page", "Different register entirely"}
        finally:
            await db.rollback()
            await db.close()


SPREAD_SCHEMA = [
    {"name": "serial_no", "type": "text", "role": "serial"},
    {"name": "owner_name", "type": "text", "half": "left"},
    {"name": "valuation", "type": "text", "half": "right"},
]


@pytest.mark.asyncio
async def test_spread_extraction_reconciles_uneven_rows_by_position():
    """TS1's generalization of T26: a right-hand band with an extra
    property row (no serial of its own) no longer sends the whole page
    pair to needs_review — it gets positionally paired to the left row
    whose vertical span contains it."""
    async with AsyncSessionLocal() as db:
        try:
            tenant_id, doc_id, version_id = await _make_doc(db, title="spread_uneven.pdf")

            left_response = _vlm_json([
                {"serial_no": _f("1", bbox=[0.1, 0.1, 0.2, 0.15]), "owner_name": _f("Priya Sharma", bbox=[0.3, 0.1, 0.6, 0.15])},
                {"serial_no": _f("2", bbox=[0.1, 0.3, 0.2, 0.5]), "owner_name": _f("Combined Entry", bbox=[0.3, 0.3, 0.6, 0.5])},
            ])
            right_response = _vlm_json([
                {"serial_no": _f("1", bbox=[0.1, 0.1, 0.2, 0.15]), "valuation": _f("100", bbox=[0.3, 0.1, 0.6, 0.15])},
                {"valuation": _f("200", bbox=[0.3, 0.30, 0.6, 0.38])},   # extra property, no serial
                {"valuation": _f("250", bbox=[0.3, 0.40, 0.6, 0.48])},   # extra property, no serial
            ])
            fake_vlm = AsyncMock()
            fake_vlm.extract_structured.side_effect = [left_response, right_response]

            written = await _extract_spread_facts(
                db, tenant_id, doc_id, version_id, _n_page_pdf_bytes(2), "pdf",
                fake_vlm, SPREAD_SCHEMA, max_pages=2,
            )
            await db.commit()

            res = await db.execute(select(Fact).where(Fact.document_id == doc_id))
            facts = res.scalars().all()
            assert not any(f.field_name == "_join_mismatch" for f in facts)

            valuations = sorted(f.value["v"] for f in facts if f.field_name == "valuation")
            assert valuations == ["100", "200", "250"]
            owners = sorted(f.value["v"] for f in facts if f.field_name == "owner_name")
            assert owners == ["Combined Entry", "Priya Sharma"]
        finally:
            await db.rollback()
            await db.close()


@pytest.mark.asyncio
async def test_ambiguous_shape_adjudicated_once_then_cached():
    """Ambiguous field-set overlap goes to the LLM once per distinct
    shape; a second occurrence of the identical shape reuses the cached
    verdict instead of asking again."""
    async with AsyncSessionLocal() as db:
        try:
            # Unique field names per run: doc_dg_table_shape_decisions is
            # keyed on shape (not document) and rows persist across test
            # runs against this shared dev DB — a hardcoded shape would
            # hit an earlier run's cached row and never call the LLM at all.
            suffix = uuid.uuid4().hex[:8]
            fa, fb, fc = f"a_{suffix}", f"b_{suffix}", f"c_{suffix}"
            full_schema = frozenset({fa, fb, fc, f"d_{suffix}"})

            fake_llm = AsyncMock()
            fake_llm.complete.return_value = '{"relation": "vertical", "confidence": 0.9, "reason": "same table"}'

            page_extractions_1 = [
                {"page_number": 1, "rows": [{fa: _f("x"), fb: _f("y")}], "marginalia": [], "page": None},
                {"page_number": 2, "rows": [{fb: _f("y2"), fc: _f("z")}], "marginalia": [], "page": None},
            ]

            import app.pipeline.vlm_extraction as vlm_mod
            from app.pipeline.table_stitch import field_set as ts_field_set, shape_hash as ts_shape_hash

            orig_get_llm = vlm_mod.get_llm_provider
            vlm_mod.get_llm_provider = lambda: fake_llm
            try:
                segments_1 = await _stitch_vertical_segments(db, page_extractions_1, full_schema, frozenset())
                await db.commit()
                assert len(segments_1) == 1  # adjudicated "vertical" -> stitched
                assert fake_llm.complete.call_count == 1

                expected_hash = ts_shape_hash(
                    ts_field_set(page_extractions_1[0]["rows"]), ts_field_set(page_extractions_1[1]["rows"])
                )
                cached = await db.execute(select(TableShapeDecision).where(TableShapeDecision.shape_hash == expected_hash))
                rows = cached.scalars().all()
                assert len(rows) == 1
                assert rows[0].relation == "vertical"
                assert rows[0].decided_by == "llm"

                # Same shape again (different page numbers, identical field sets) —
                # must hit the cache, not call the LLM a second time.
                page_extractions_2 = [
                    {"page_number": 5, "rows": [{fa: _f("p"), fb: _f("q")}], "marginalia": [], "page": None},
                    {"page_number": 6, "rows": [{fb: _f("q2"), fc: _f("r")}], "marginalia": [], "page": None},
                ]
                segments_2 = await _stitch_vertical_segments(db, page_extractions_2, full_schema, frozenset())
                await db.commit()
                assert len(segments_2) == 1
                assert fake_llm.complete.call_count == 1  # unchanged — cache hit
            finally:
                vlm_mod.get_llm_provider = orig_get_llm
        finally:
            await db.rollback()
            await db.close()


@pytest.mark.asyncio
async def test_adjudication_unavailable_defaults_to_not_stitching():
    """Air-gapped / no local LLM must degrade safely: ambiguous stays
    separate segments rather than guessing."""
    async with AsyncSessionLocal() as db:
        try:
            import app.pipeline.vlm_extraction as vlm_mod

            def _raise_air_gapped():
                raise RuntimeError("AIR_GAPPED=true, no local LLM provider")

            fields_a = frozenset({"m", "n"})
            fields_b = frozenset({"n", "o"})
            page_extractions = [
                {"page_number": 1, "rows": [{"m": _f("x"), "n": _f("y")}], "marginalia": [], "page": None},
                {"page_number": 2, "rows": [{"n": _f("y2"), "o": _f("z")}], "marginalia": [], "page": None},
            ]

            orig_get_llm = vlm_mod.get_llm_provider
            vlm_mod.get_llm_provider = _raise_air_gapped
            try:
                segments = await _stitch_vertical_segments(db, page_extractions, frozenset({"m", "n", "o", "p"}), frozenset())
                await db.commit()
                assert len(segments) == 2  # not stitched — safe default
            finally:
                vlm_mod.get_llm_provider = orig_get_llm
        finally:
            await db.rollback()
            await db.close()
