import uuid

import pytest

from app.database import AsyncSessionLocal
from app.models.tenant import Tenant
from app.models.user import User
from app.models.document import Document
from app.models.document_version import DocumentVersion
from app.models.chunk import Chunk
from app.services.duplicate_service import resolve_duplicate_representatives


async def _make_tenant(db):
    tenant_id = uuid.uuid4()
    user_id = uuid.uuid4()
    tenant = Tenant(id=tenant_id, name=f"Dup Tenant {uuid.uuid4().hex[:6]}")
    user = User(id=user_id, tenant_id=tenant_id, email=f"dup_{uuid.uuid4().hex[:6]}@test.com", hashed_password="pw")
    db.add_all([tenant, user])
    await db.flush()
    return tenant_id, user_id


async def _make_doc_with_chunk0(db, tenant_id, title, embedding):
    doc = Document(id=uuid.uuid4(), tenant_id=tenant_id, title=title, status="indexed")
    version = DocumentVersion(
        id=uuid.uuid4(), tenant_id=tenant_id, document_id=doc.id, version_number=1, s3_path="x",
        file_hash=uuid.uuid4().hex, file_size_bytes=1, original_filename=title,
    )
    db.add_all([doc, version])
    await db.flush()
    doc.current_version_id = version.id
    chunk = Chunk(
        id=uuid.uuid4(), document_id=doc.id, version_id=version.id, tenant_id=tenant_id,
        content="representative first-chunk content", embedding=embedding,
        chunk_metadata={}, page_number=1, chunk_index=0, s3_path="x",
    )
    db.add(chunk)
    await db.flush()
    return doc.id


_VEC_A = [1.0] + [0.0] * 1023  # identical to _VEC_A_RESCAN -> cosine similarity 1.0
_VEC_A_RESCAN = [1.0] + [0.0] * 1023
_VEC_B = [0.0] * 1023 + [1.0]  # orthogonal to _VEC_A -> cosine similarity 0.0


@pytest.mark.asyncio
async def test_near_duplicate_documents_collapse_to_the_higher_ranked_representative():
    """Real bug found live (verification report, 2026-09-09): a chat
    citation pointed at a different document than the one named in the
    user's question, because the corpus has near-duplicate scans of the
    same underlying register. Two documents whose chunk_index=0
    embeddings are identical (cosine similarity 1.0, comfortably over the
    0.92 default threshold) must collapse to a single representative --
    whichever one is listed first, i.e. ranked higher."""
    async with AsyncSessionLocal() as db:
        try:
            tenant_id, _ = await _make_tenant(db)
            doc_higher = await _make_doc_with_chunk0(db, tenant_id, "demo_test_document.pdf", _VEC_A)
            doc_lower = await _make_doc_with_chunk0(db, tenant_id, "demo_test_document_rescan.pdf", _VEC_A_RESCAN)
            await db.commit()

            representative = await resolve_duplicate_representatives(db, tenant_id, [doc_higher, doc_lower])
            assert representative[doc_higher] == doc_higher
            assert representative[doc_lower] == doc_higher, (
                "the lower-ranked near-duplicate must resolve to the higher-ranked document's id -- "
                "if this is doc_lower instead, a lower-ranked duplicate's content would still leak "
                "into search results/citations ahead of the one actually worth surfacing"
            )
        finally:
            await db.rollback()
            await db.close()


@pytest.mark.asyncio
async def test_genuinely_different_documents_each_stay_their_own_representative():
    """The fix must never collapse two documents that merely share a
    topic -- only near-IDENTICAL content (real rescans), matching the
    same high threshold find_fuzzy_duplicates already uses at upload
    time. Two orthogonal embeddings (cosine similarity 0.0) are nowhere
    close to that threshold."""
    async with AsyncSessionLocal() as db:
        try:
            tenant_id, _ = await _make_tenant(db)
            doc_a = await _make_doc_with_chunk0(db, tenant_id, "Aurangabad-Shia.pdf", _VEC_A)
            doc_b = await _make_doc_with_chunk0(db, tenant_id, "Wardha.pdf", _VEC_B)
            await db.commit()

            representative = await resolve_duplicate_representatives(db, tenant_id, [doc_a, doc_b])
            assert representative[doc_a] == doc_a
            assert representative[doc_b] == doc_b
        finally:
            await db.rollback()
            await db.close()


@pytest.mark.asyncio
async def test_single_document_input_is_a_trivial_identity_mapping():
    """A single-candidate search (the overwhelmingly common case) must
    never pay for a self-join query it can't possibly need anything
    from -- short-circuited before any DB call."""
    async with AsyncSessionLocal() as db:
        try:
            tenant_id, _ = await _make_tenant(db)
            doc_id = uuid.uuid4()
            representative = await resolve_duplicate_representatives(db, tenant_id, [doc_id])
            assert representative == {doc_id: doc_id}
        finally:
            await db.rollback()
            await db.close()


@pytest.mark.asyncio
async def test_empty_input_returns_empty_mapping():
    async with AsyncSessionLocal() as db:
        try:
            tenant_id, _ = await _make_tenant(db)
            assert await resolve_duplicate_representatives(db, tenant_id, []) == {}
        finally:
            await db.rollback()
            await db.close()
