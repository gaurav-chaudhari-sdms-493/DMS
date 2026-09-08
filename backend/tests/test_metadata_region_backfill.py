"""T05 — the backfill script's DB-facing half: reconstructing per-page
word_regions from already-persisted doc_dg_chunks rows and writing real
doc_dg_metadata_item_regions from them. source_location_service's own
tests already cover the matching algorithm in isolation; this proves the
DB plumbing around it (chunk -> pages reconstruction, region insert) works
against a real Postgres instance, not just in-memory dicts.

Unlike this project's other throwaway-tenant tests, nothing here writes an
audit-log entry, so there's no append-only-table FK blocking a real
DELETE -- every test cleans up its own tenant/document/chunk/metadata
rows in full, in FK order, instead of leaving them behind.

Worth knowing if you're debugging a run of this file: backfill() is
deliberately global, not scoped to one tenant or document (that's its
whole job) -- so a real, non-dry-run call here does a real, full pass over
every metadata item in the actual database, not just this test's own
throwaway rows. Confirmed live 2026-09-07: this incidentally backfilled a
handful of pre-existing real (if synthetic/test-origin) metadata items
that already had locatable word regions sitting unused. That's correct,
wanted behavior (backfill is additive and idempotent, never overwrites an
existing region -- see test_backfill_never_overwrites_an_existing_region
below), not test pollution, and nothing to clean up."""
import uuid

import pytest
from sqlalchemy import delete, select

from app.database import AsyncSessionLocal
from app.models.chunk import Chunk
from app.models.document import Document
from app.models.document_version import DocumentVersion
from app.models.metadata_item import MetadataItem
from app.models.metadata_item_region import MetadataItemRegion
from app.models.tenant import Tenant
from app.models.user import User
from app.services.auth_service import hash_password
from scripts.backfill_metadata_regions import backfill, _pages_from_chunks


async def _make_doc_with_chunks(db, page_words, chunk_content):
    tenant_id = uuid.uuid4()
    tenant = Tenant(id=tenant_id, name=f"T05 Backfill Tenant {uuid.uuid4().hex[:6]}")
    user = User(id=uuid.uuid4(), tenant_id=tenant_id, email=f"t05_{uuid.uuid4().hex[:8]}@test.com", hashed_password=hash_password("x"))
    db.add_all([tenant, user])
    await db.flush()

    doc = Document(id=uuid.uuid4(), tenant_id=tenant_id, title="register.pdf", status="indexed")
    version = DocumentVersion(
        id=uuid.uuid4(), tenant_id=tenant_id, document_id=doc.id, version_number=1, s3_path="x",
        file_hash=uuid.uuid4().hex, file_size_bytes=1, original_filename="register.pdf",
    )
    db.add_all([doc, version])
    await db.flush()
    doc.current_version_id = version.id
    await db.flush()

    chunk = Chunk(
        id=uuid.uuid4(), document_id=doc.id, version_id=version.id, tenant_id=tenant_id,
        content=chunk_content, embedding=[0.0] * 1024,
        chunk_metadata={"token_count": 10, "bbox": {}, "word_regions": page_words},
        page_number=1, chunk_index=0, s3_path="x",
    )
    db.add(chunk)
    await db.flush()

    return tenant_id, doc.id


async def _cleanup(tenant_id, doc_id):
    """backfill() commits through its own, separate session -- this test's
    own db.rollback() can't undo that. Delete everything for real, in FK
    order, through a fresh session instead."""
    async with AsyncSessionLocal() as db:
        await db.execute(delete(MetadataItemRegion).where(MetadataItemRegion.tenant_id == tenant_id))
        await db.execute(delete(MetadataItem).where(MetadataItem.document_id == doc_id))
        await db.execute(delete(Chunk).where(Chunk.tenant_id == tenant_id))
        await db.execute(
            Document.__table__.update().where(Document.id == doc_id).values(current_version_id=None)
        )
        await db.execute(delete(DocumentVersion).where(DocumentVersion.document_id == doc_id))
        await db.execute(delete(Document).where(Document.id == doc_id))
        await db.execute(delete(User).where(User.tenant_id == tenant_id))
        await db.execute(delete(Tenant).where(Tenant.id == tenant_id))
        await db.commit()


@pytest.mark.asyncio
async def test_pages_from_chunks_reconstructs_word_regions():
    words = [{"text": "WB-77", "x0": 0.2, "y0": 0.1, "x1": 0.3, "y1": 0.12}]
    async with AsyncSessionLocal() as db:
        try:
            tenant_id, doc_id = await _make_doc_with_chunks(db, words, "Serial WB-77 recorded")
            doc = await db.get(Document, doc_id)
            pages = await _pages_from_chunks(db, doc.current_version_id)
            assert len(pages) == 1
            assert pages[0]["page_number"] == 1
            assert pages[0]["words"] == words
            assert "WB-77" in pages[0]["text"]
        finally:
            # Nothing was committed on this path -- rollback is enough.
            await db.rollback()


@pytest.mark.asyncio
async def test_backfill_writes_a_real_region_for_an_existing_metadata_item():
    words = [
        {"text": "Serial", "x0": 0.1, "y0": 0.1, "x1": 0.18, "y1": 0.12},
        {"text": "WB-88", "x0": 0.19, "y0": 0.1, "x1": 0.27, "y1": 0.12},
        {"text": "recorded", "x0": 0.28, "y0": 0.1, "x1": 0.4, "y1": 0.12},
    ]
    async with AsyncSessionLocal() as db:
        tenant_id, doc_id = await _make_doc_with_chunks(db, words, "Serial WB-88 recorded")
        item = MetadataItem(tenant_id=tenant_id, document_id=doc_id, key="serial_number", value={"v": "WB-88"}, source="llm", confidence_score=0.9)
        db.add(item)
        await db.commit()
        item_id = item.id

    try:
        await backfill(dry_run=False)

        async with AsyncSessionLocal() as db:
            res = await db.execute(select(MetadataItemRegion).where(MetadataItemRegion.metadata_item_id == item_id))
            region = res.scalar_one()
            assert region.page_number == 1
            assert region.x0 == pytest.approx(0.19)
            assert region.x1 == pytest.approx(0.27)
            assert region.tenant_id == tenant_id
    finally:
        await _cleanup(tenant_id, doc_id)


@pytest.mark.asyncio
async def test_backfill_dry_run_writes_nothing():
    words = [{"text": "WB-99", "x0": 0.2, "y0": 0.1, "x1": 0.3, "y1": 0.12}]
    async with AsyncSessionLocal() as db:
        tenant_id, doc_id = await _make_doc_with_chunks(db, words, "Serial WB-99 recorded")
        item = MetadataItem(tenant_id=tenant_id, document_id=doc_id, key="serial_number", value={"v": "WB-99"}, source="llm", confidence_score=0.9)
        db.add(item)
        await db.commit()
        item_id = item.id

    try:
        await backfill(dry_run=True)
        async with AsyncSessionLocal() as db:
            res = await db.execute(select(MetadataItemRegion).where(MetadataItemRegion.metadata_item_id == item_id))
            assert res.scalar_one_or_none() is None
    finally:
        await _cleanup(tenant_id, doc_id)


@pytest.mark.asyncio
async def test_backfill_never_overwrites_an_existing_region():
    """Safe to re-run: a metadata item that already has a region (written
    at ingest time by the fix in worker.py) must be left alone, not
    re-matched and duplicated."""
    words = [{"text": "WB-11", "x0": 0.2, "y0": 0.1, "x1": 0.3, "y1": 0.12}]
    async with AsyncSessionLocal() as db:
        tenant_id, doc_id = await _make_doc_with_chunks(db, words, "Serial WB-11 recorded")
        item = MetadataItem(tenant_id=tenant_id, document_id=doc_id, key="serial_number", value={"v": "WB-11"}, source="llm", confidence_score=0.9)
        db.add(item)
        await db.flush()
        db.add(MetadataItemRegion(
            tenant_id=tenant_id, metadata_item_id=item.id, page_number=5,
            x0=0.0, y0=0.0, x1=1.0, y1=1.0,
        ))
        await db.commit()
        item_id = item.id

    try:
        await backfill(dry_run=False)
        async with AsyncSessionLocal() as db:
            res = await db.execute(select(MetadataItemRegion).where(MetadataItemRegion.metadata_item_id == item_id))
            regions = res.scalars().all()
            assert len(regions) == 1
            assert regions[0].page_number == 5  # untouched, not re-matched to page 1
    finally:
        await _cleanup(tenant_id, doc_id)
