import pytest
import uuid
from fastapi import HTTPException
from app.database import AsyncSessionLocal
from app.models.tenant import Tenant
from app.models.user import User
from app.models.folder import Folder
from app.models.document import Document
from app.models.document_version import DocumentVersion
from app.models.fact import Fact
from app.services.fact_verification_service import confirm_fact, bulk_confirm_facts
from app.services.corpus_calibration_service import calibrate_corpus


async def _make_corpus(db):
    """T55 test fixture: tenant, actor, a calibrated corpus folder, one
    document in it, and returns them for the caller to add facts to."""
    tenant_id = uuid.uuid4()
    actor_id = uuid.uuid4()
    tenant = Tenant(id=tenant_id, name=f"T55 Tenant {uuid.uuid4().hex[:6]}")
    user = User(id=actor_id, tenant_id=tenant_id, email=f"t55_{uuid.uuid4().hex[:6]}@test.com", hashed_password="pw")
    folder = Folder(id=uuid.uuid4(), tenant_id=tenant_id, name="T55 Corpus")
    db.add_all([tenant, user, folder])
    await db.flush()

    doc = Document(id=uuid.uuid4(), tenant_id=tenant_id, title="T55 doc", status="indexed", folder_id=folder.id)
    version = DocumentVersion(
        id=uuid.uuid4(), document_id=doc.id, version_number=1, s3_path="x",
        file_hash="deadbeef", file_size_bytes=1, original_filename="t55.pdf",
    )
    db.add_all([doc, version])
    await db.flush()
    doc.current_version_id = version.id
    await db.flush()

    await calibrate_corpus(db, tenant_id, folder.id, actor_id, sample_size=10, notes="T55 test calibration")

    return tenant_id, actor_id, folder.id, doc.id, version.id


def _make_fact(tenant_id, doc_id, version_id, *, status="in_review", confidence=0.9, is_handwritten=False):
    return Fact(
        id=uuid.uuid4(), tenant_id=tenant_id, document_id=doc_id, version_id=version_id,
        field_name="owner_name", value={"v": "Test Value"}, confidence=confidence,
        status=status, is_handwritten=is_handwritten,
    )


@pytest.mark.asyncio
async def test_confirm_fact_requires_actor():
    async with AsyncSessionLocal() as db:
        try:
            tenant_id, actor_id, folder_id, doc_id, version_id = await _make_corpus(db)
            fact = _make_fact(tenant_id, doc_id, version_id)
            db.add(fact)
            await db.flush()

            with pytest.raises(ValueError):
                await confirm_fact(db, tenant_id, fact.id, None)
        finally:
            await db.rollback()
            await db.close()


@pytest.mark.asyncio
async def test_confirm_fact_rejects_machine_status():
    """T51 — an auto-committed ('machine') fact is never promoted through
    confirmation, same rule as tier1/2 entity edges."""
    async with AsyncSessionLocal() as db:
        try:
            tenant_id, actor_id, folder_id, doc_id, version_id = await _make_corpus(db)
            fact = _make_fact(tenant_id, doc_id, version_id, status="machine")
            db.add(fact)
            await db.flush()

            with pytest.raises(HTTPException) as exc_info:
                await confirm_fact(db, tenant_id, fact.id, actor_id)
            assert exc_info.value.status_code == 409
        finally:
            await db.rollback()
            await db.close()


@pytest.mark.asyncio
async def test_confirm_fact_promotes_in_review_to_verified_with_real_actor_event():
    """T55 — no promotion to verified without an actor event: the happy
    path itself proves the actor/timestamp are actually recorded, not
    just that the status flips."""
    async with AsyncSessionLocal() as db:
        try:
            tenant_id, actor_id, folder_id, doc_id, version_id = await _make_corpus(db)
            fact = _make_fact(tenant_id, doc_id, version_id, status="in_review")
            db.add(fact)
            await db.flush()

            confirmed = await confirm_fact(db, tenant_id, fact.id, actor_id)
            assert confirmed.status == "verified"
            assert confirmed.verified_by_actor_id == actor_id
            assert confirmed.verified_at is not None
        finally:
            await db.rollback()
            await db.close()


@pytest.mark.asyncio
async def test_bulk_confirm_requires_actor():
    async with AsyncSessionLocal() as db:
        try:
            tenant_id, actor_id, folder_id, doc_id, version_id = await _make_corpus(db)
            with pytest.raises(ValueError):
                await bulk_confirm_facts(db, tenant_id, folder_id, 0.8, None, "policy-v1")
        finally:
            await db.rollback()
            await db.close()


@pytest.mark.asyncio
async def test_bulk_confirm_requires_policy_version():
    async with AsyncSessionLocal() as db:
        try:
            tenant_id, actor_id, folder_id, doc_id, version_id = await _make_corpus(db)
            with pytest.raises(ValueError):
                await bulk_confirm_facts(db, tenant_id, folder_id, 0.8, actor_id, "")
        finally:
            await db.rollback()
            await db.close()


@pytest.mark.asyncio
async def test_bulk_confirm_requires_calibrated_corpus():
    """T59's gate, reused here: bulk acceptance is disabled on a corpus
    nobody has calibrated — even with a valid actor and policy version."""
    async with AsyncSessionLocal() as db:
        try:
            tenant_id = uuid.uuid4()
            actor_id = uuid.uuid4()
            tenant = Tenant(id=tenant_id, name=f"Uncalibrated Tenant {uuid.uuid4().hex[:6]}")
            user = User(id=actor_id, tenant_id=tenant_id, email=f"uncal_{uuid.uuid4().hex[:6]}@test.com", hashed_password="pw")
            folder = Folder(id=uuid.uuid4(), tenant_id=tenant_id, name="Uncalibrated Corpus")
            db.add_all([tenant, user, folder])
            await db.flush()

            with pytest.raises(HTTPException) as exc_info:
                await bulk_confirm_facts(db, tenant_id, folder.id, 0.8, actor_id, "policy-v1")
            assert exc_info.value.status_code == 409
        finally:
            await db.rollback()
            await db.close()


@pytest.mark.asyncio
async def test_bulk_confirm_never_promotes_handwritten_facts():
    """T55's core hard rule: no handwritten-source verified data without
    confirmation. A handwritten fact above threshold in a calibrated
    corpus must still be excluded from bulk promotion — only
    confirm_fact() (one person, one fact) may verify it."""
    async with AsyncSessionLocal() as db:
        try:
            tenant_id, actor_id, folder_id, doc_id, version_id = await _make_corpus(db)
            handwritten_fact = _make_fact(tenant_id, doc_id, version_id, confidence=0.99, is_handwritten=True)
            typed_fact = _make_fact(tenant_id, doc_id, version_id, confidence=0.95, is_handwritten=False)
            db.add_all([handwritten_fact, typed_fact])
            await db.flush()

            result = await bulk_confirm_facts(db, tenant_id, folder_id, 0.8, actor_id, "policy-v1")

            assert typed_fact.id in result["fact_ids"]
            assert handwritten_fact.id not in result["fact_ids"]

            await db.refresh(handwritten_fact)
            await db.refresh(typed_fact)
            assert handwritten_fact.status == "in_review"  # untouched
            assert typed_fact.status == "verified"
        finally:
            await db.rollback()
            await db.close()
