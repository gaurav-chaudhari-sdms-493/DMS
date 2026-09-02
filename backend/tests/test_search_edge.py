import pytest
import uuid
from app.services.search_service import search
from app.services.chat_service import _extract_score_threshold, _is_explicit_search_intent
from app.database import AsyncSessionLocal
from app.models.tenant import Tenant
from app.models.user import User
from app.models.document import Document
from app.models.document_version import DocumentVersion
from app.models.chunk import Chunk
from app.models.fact import Fact
from app.models.fact_region import FactRegion
from app.models.page import DocumentPage


def test_extract_score_threshold_edge_cases():
    """Verify extracting score thresholds from dynamic chat queries."""
    assert _extract_score_threshold("filter score >= 95%") == 0.95
    assert _extract_score_threshold("score >= 100%") == 1.0
    assert _extract_score_threshold("score >= 0%") == 0.0
    assert _extract_score_threshold("score > 50") == 0.50
    assert _extract_score_threshold("give me top 5 documents") is None
    assert _extract_score_threshold("random query without score") is None


def test_explicit_search_intent_detection():
    """Verify detecting user query explicit search intent triggers."""
    assert _is_explicit_search_intent("search for Q3 financial reports") is True
    assert _is_explicit_search_intent("find invoice 104") is True
    assert _is_explicit_search_intent("look for contract details") is True
    assert _is_explicit_search_intent("what is the total revenue listed on page 3?") is False


@pytest.mark.asyncio
async def test_search_isolated_tenant_empty_results():
    """Verify searching in a newly created empty tenant returns 0 results cleanly without errors."""
    async with AsyncSessionLocal() as db:
        try:
            tenant_id = uuid.uuid4()
            user_id = uuid.uuid4()
            tenant = Tenant(id=tenant_id, name=f"Empty Tenant {uuid.uuid4().hex[:6]}")
            user = User(id=user_id, tenant_id=tenant_id, email=f"empty_{uuid.uuid4().hex[:6]}@test.com", hashed_password="pw")
            db.add_all([tenant, user])
            await db.commit()

            res = await search(
                query="test query for empty tenant",
                tenant_id=tenant_id,
                user_id=user_id,
                limit=10,
                filters=None,
                db=db,
                ip_address="127.0.0.1"
            )
            assert res is not None
            assert len(res.results) == 0
        finally:
            await db.close()


@pytest.mark.asyncio
async def test_search_fuzzy_leg_catches_misspelled_proper_noun():
    """T72 — a typo'd proper noun ("Depshmukh" for "Deshmukh") has zero
    keyword tsvector matches and an unreliable vector-semantic match, but
    word_similarity() finds it. rerank_provider is forced to 'bgem3'
    (local) so this test doesn't depend on a live, rate-limited Cohere key."""
    async with AsyncSessionLocal() as db:
        try:
            tenant_id = uuid.uuid4()
            user_id = uuid.uuid4()
            tenant = Tenant(id=tenant_id, name=f"Fuzzy Tenant {uuid.uuid4().hex[:6]}")
            user = User(id=user_id, tenant_id=tenant_id, email=f"fuzzy_{uuid.uuid4().hex[:6]}@test.com", hashed_password="pw")
            db.add_all([tenant, user])
            await db.commit()

            doc = Document(id=uuid.uuid4(), tenant_id=tenant_id, title="Deshmukh bio", status="indexed")
            version = DocumentVersion(
                id=uuid.uuid4(), document_id=doc.id, version_number=1, s3_path="x",
                file_hash="deadbeef", file_size_bytes=1, original_filename="deshmukh.txt",
            )
            db.add_all([doc, version])
            await db.flush()
            doc.current_version_id = version.id
            chunk = Chunk(
                id=uuid.uuid4(), document_id=doc.id, version_id=version.id, tenant_id=tenant_id,
                content="A short biography of Priya Deshmukh, compliance officer.",
                embedding=[0.0] * 1024, chunk_metadata={}, page_number=1, chunk_index=0, s3_path="x",
            )
            db.add(chunk)
            await db.commit()

            res = await search(
                query="Depshmukh",
                tenant_id=tenant_id,
                user_id=user_id,
                limit=10,
                filters=None,
                db=db,
                ip_address="127.0.0.1",
                rerank_provider="bgem3",
                generate_summary=False,
            )
            assert len(res.results) >= 1
            assert "fuzzy" in res.search_mode
        finally:
            await db.close()


async def _make_doc_with_fact(db, tenant_id, field_name, value, chunk_content):
    """A document whose chunk text does NOT contain the extracted field's
    value verbatim — the only way to find it is the structured-record leg."""
    doc = Document(id=uuid.uuid4(), tenant_id=tenant_id, title="Property Register", status="indexed")
    version = DocumentVersion(
        id=uuid.uuid4(), document_id=doc.id, version_number=1, s3_path="x",
        file_hash=uuid.uuid4().hex, file_size_bytes=1, original_filename="reg.pdf",
    )
    db.add_all([doc, version])
    await db.flush()
    doc.current_version_id = version.id

    chunk = Chunk(
        id=uuid.uuid4(), document_id=doc.id, version_id=version.id, tenant_id=tenant_id,
        content=chunk_content, embedding=[0.0] * 1024, chunk_metadata={}, page_number=1, chunk_index=0, s3_path="x",
    )
    page = DocumentPage(
        id=uuid.uuid4(), tenant_id=tenant_id, document_id=doc.id, version_id=version.id,
        page_number=1, width=612, height=792,
    )
    db.add_all([chunk, page])
    await db.flush()

    fact = Fact(
        id=uuid.uuid4(), tenant_id=tenant_id, document_id=doc.id, version_id=version.id,
        field_name=field_name, value={"v": value}, confidence=0.9, status="machine",
    )
    db.add(fact)
    await db.flush()
    db.add(FactRegion(id=uuid.uuid4(), tenant_id=tenant_id, fact_id=fact.id, page_id=page.id, x0=0.1, y0=0.1, x1=0.5, y1=0.2))
    await db.commit()
    return doc, fact


@pytest.mark.asyncio
async def test_search_structured_record_leg_finds_field_absent_from_chunk_text():
    """T73 — a value that only exists as an extracted Fact field (never
    verbatim in the chunk's running OCR text) is still findable and cited
    by fact_id, with search_mode reporting the 'structured' leg."""
    async with AsyncSessionLocal() as db:
        try:
            tenant_id = uuid.uuid4()
            user_id = uuid.uuid4()
            tenant = Tenant(id=tenant_id, name=f"Structured Tenant {uuid.uuid4().hex[:6]}")
            user = User(id=user_id, tenant_id=tenant_id, email=f"struct_{uuid.uuid4().hex[:6]}@test.com", hashed_password="pw")
            db.add_all([tenant, user])
            await db.commit()

            doc, fact = await _make_doc_with_fact(
                db, tenant_id, field_name="survey_no", value="42/1B-Kolhapur",
                chunk_content="A register page listing property entries for the district office.",
            )

            res = await search(
                query="42/1B-Kolhapur",
                tenant_id=tenant_id,
                user_id=user_id,
                limit=10,
                filters=None,
                db=db,
                ip_address="127.0.0.1",
                rerank_provider="bgem3",
                generate_summary=False,
            )
            assert len(res.results) >= 1
            assert "structured" in res.search_mode
            assert any(r.metadata.get("fact_id") == str(fact.id) for r in res.results)
        finally:
            await db.close()


@pytest.mark.asyncio
async def test_search_filter_matches_structured_fact_field():
    """T73 — 'a query can filter on area, village or status': a filters
    dict keyed on a template field name (not a generic metadata key)
    narrows results to documents whose extracted Fact matches."""
    async with AsyncSessionLocal() as db:
        try:
            tenant_id = uuid.uuid4()
            user_id = uuid.uuid4()
            tenant = Tenant(id=tenant_id, name=f"FilterFact Tenant {uuid.uuid4().hex[:6]}")
            user = User(id=user_id, tenant_id=tenant_id, email=f"filterfact_{uuid.uuid4().hex[:6]}@test.com", hashed_password="pw")
            db.add_all([tenant, user])
            await db.commit()

            matching_doc, _ = await _make_doc_with_fact(
                db, tenant_id, field_name="village", value="Washim",
                chunk_content="Register entry for a plot, area five hundred square metres.",
            )
            other_doc, _ = await _make_doc_with_fact(
                db, tenant_id, field_name="village", value="Basmath",
                chunk_content="Register entry for a plot, area five hundred square metres.",
            )

            res = await search(
                query="plot area",
                tenant_id=tenant_id,
                user_id=user_id,
                limit=10,
                filters={"village": "Washim"},
                db=db,
                ip_address="127.0.0.1",
                rerank_provider="bgem3",
                generate_summary=False,
            )
            result_doc_ids = {str(r.document_id) for r in res.results}
            assert str(matching_doc.id) in result_doc_ids
            assert str(other_doc.id) not in result_doc_ids
        finally:
            await db.close()
