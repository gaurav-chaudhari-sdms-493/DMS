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
from app.services.fact_verification_service import (
    confirm_fact, bulk_confirm_facts, mark_fact_handwritten, get_adjudication_queue,
    bulk_edit_facts, revert_bulk_edit_batch, resolve_stitch_ambiguity,
)
from app.services.corpus_calibration_service import calibrate_corpus
from app.services import field_trust_service, table_shape_service


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


def _make_fact(tenant_id, doc_id, version_id, *, status="in_review", confidence=0.9, is_handwritten=False, field_name="owner_name"):
    return Fact(
        id=uuid.uuid4(), tenant_id=tenant_id, document_id=doc_id, version_id=version_id,
        field_name=field_name, value={"v": "Test Value"}, confidence=confidence,
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


@pytest.mark.asyncio
async def test_mark_fact_handwritten_requires_actor():
    async with AsyncSessionLocal() as db:
        try:
            tenant_id, actor_id, folder_id, doc_id, version_id = await _make_corpus(db)
            fact = _make_fact(tenant_id, doc_id, version_id, status="machine")
            db.add(fact)
            await db.flush()

            with pytest.raises(ValueError):
                await mark_fact_handwritten(db, tenant_id, fact.id, None)
        finally:
            await db.rollback()
            await db.close()


@pytest.mark.asyncio
async def test_mark_fact_handwritten_demotes_machine_to_in_review():
    """T30 — operator capture: a machine-committed fact discovered to be
    handwritten can't stay in an auto-committed, never-reviewed state."""
    async with AsyncSessionLocal() as db:
        try:
            tenant_id, actor_id, folder_id, doc_id, version_id = await _make_corpus(db)
            fact = _make_fact(tenant_id, doc_id, version_id, status="machine", is_handwritten=False)
            db.add(fact)
            await db.flush()

            updated = await mark_fact_handwritten(db, tenant_id, fact.id, actor_id)
            assert updated.is_handwritten is True
            assert updated.status == "in_review"
        finally:
            await db.rollback()
            await db.close()


@pytest.mark.asyncio
async def test_mark_fact_handwritten_leaves_verified_facts_verified():
    async with AsyncSessionLocal() as db:
        try:
            tenant_id, actor_id, folder_id, doc_id, version_id = await _make_corpus(db)
            fact = _make_fact(tenant_id, doc_id, version_id, status="verified", is_handwritten=False)
            db.add(fact)
            await db.flush()

            updated = await mark_fact_handwritten(db, tenant_id, fact.id, actor_id)
            assert updated.is_handwritten is True
            assert updated.status == "verified"
        finally:
            await db.rollback()
            await db.close()


@pytest.mark.asyncio
async def test_adjudication_queue_marginalia_and_handwritten_are_disjoint():
    """T30 — a '_marginalia' fact only shows up under 'marginalia', never
    'handwritten', even though it's always is_handwritten=True."""
    async with AsyncSessionLocal() as db:
        try:
            tenant_id, actor_id, folder_id, doc_id, version_id = await _make_corpus(db)
            handwritten_field = Fact(
                id=uuid.uuid4(), tenant_id=tenant_id, document_id=doc_id, version_id=version_id,
                field_name="owner_name", value={"v": "Illegible"}, confidence=0.6,
                status="in_review", is_handwritten=True,
            )
            marginalia_note = Fact(
                id=uuid.uuid4(), tenant_id=tenant_id, document_id=doc_id, version_id=version_id,
                field_name="_marginalia", value={"v": "disputed boundary"}, confidence=None,
                status="in_review", is_handwritten=True,
            )
            db.add_all([handwritten_field, marginalia_note])
            await db.flush()

            handwritten_queue = await get_adjudication_queue(db, tenant_id, category="handwritten")
            marginalia_queue = await get_adjudication_queue(db, tenant_id, category="marginalia")

            handwritten_ids = {f["fact_id"] for f in handwritten_queue["facts"]}
            marginalia_ids = {f["fact_id"] for f in marginalia_queue["facts"]}

            assert str(handwritten_field.id) in handwritten_ids
            assert str(marginalia_note.id) not in handwritten_ids
            assert str(marginalia_note.id) in marginalia_ids
            assert str(handwritten_field.id) not in marginalia_ids
        finally:
            await db.rollback()
            await db.close()


@pytest.mark.asyncio
async def test_adjudication_queue_join_mismatch_filters_on_sentinel_field():
    """T26 — a '_join_mismatch' fact (written by the spread-join path
    when it can't match serials across a page pair) only shows up under
    'join_mismatch', never 'low_confidence' or 'marginalia'."""
    async with AsyncSessionLocal() as db:
        try:
            tenant_id, actor_id, folder_id, doc_id, version_id = await _make_corpus(db)
            mismatch_fact = Fact(
                id=uuid.uuid4(), tenant_id=tenant_id, document_id=doc_id, version_id=version_id,
                field_name="_join_mismatch",
                value={"reason": "left/right disagree on serials", "left_page": 3, "right_page": 4},
                confidence=None, status="in_review", is_handwritten=False,
            )
            db.add(mismatch_fact)
            await db.flush()

            queue = await get_adjudication_queue(db, tenant_id, category="join_mismatch")
            assert queue["total"] == 1
            assert queue["facts"][0]["fact_id"] == str(mismatch_fact.id)

            marginalia_queue = await get_adjudication_queue(db, tenant_id, category="marginalia")
            assert str(mismatch_fact.id) not in {f["fact_id"] for f in marginalia_queue["facts"]}
        finally:
            await db.rollback()
            await db.close()


@pytest.mark.asyncio
async def test_bulk_edit_facts_requires_actor():
    async with AsyncSessionLocal() as db:
        try:
            tenant_id, actor_id, folder_id, doc_id, version_id = await _make_corpus(db)
            fact = _make_fact(tenant_id, doc_id, version_id, status="machine")
            db.add(fact)
            await db.flush()

            with pytest.raises(ValueError):
                await bulk_edit_facts(db, tenant_id, [{"fact_id": fact.id, "new_value": {"v": "Corrected"}}], None)
        finally:
            await db.rollback()
            await db.close()


@pytest.mark.asyncio
async def test_bulk_edit_facts_dry_run_writes_nothing():
    async with AsyncSessionLocal() as db:
        try:
            tenant_id, actor_id, folder_id, doc_id, version_id = await _make_corpus(db)
            fact = _make_fact(tenant_id, doc_id, version_id, status="machine")
            db.add(fact)
            await db.flush()

            result = await bulk_edit_facts(
                db, tenant_id, [{"fact_id": fact.id, "new_value": {"v": "Corrected"}}], actor_id, dry_run=True,
            )
            assert result["dry_run"] is True
            assert result["changed_count"] == 1
            assert result["batch_id"] is None
            assert result["rows"][0]["previous_value"] == {"v": "Test Value"}
            assert result["rows"][0]["new_value"] == {"v": "Corrected"}

            await db.refresh(fact)
            assert fact.value == {"v": "Test Value"}
            assert fact.status == "machine"
        finally:
            await db.rollback()
            await db.close()


@pytest.mark.asyncio
async def test_bulk_edit_facts_never_promotes_to_verified():
    """T80's hard rule: editing a machine-committed value always demotes
    it to in_review — it can never come out of a bulk edit 'verified'."""
    async with AsyncSessionLocal() as db:
        try:
            tenant_id, actor_id, folder_id, doc_id, version_id = await _make_corpus(db)
            fact = _make_fact(tenant_id, doc_id, version_id, status="machine")
            db.add(fact)
            await db.flush()

            result = await bulk_edit_facts(
                db, tenant_id, [{"fact_id": fact.id, "new_value": {"v": "Corrected"}}], actor_id,
            )
            assert result["changed_count"] == 1
            assert result["batch_id"] is not None

            await db.refresh(fact)
            assert fact.value == {"v": "Corrected"}
            assert fact.status == "in_review"
        finally:
            await db.rollback()
            await db.close()


@pytest.mark.asyncio
async def test_bulk_edit_facts_clears_prior_verification():
    async with AsyncSessionLocal() as db:
        try:
            tenant_id, actor_id, folder_id, doc_id, version_id = await _make_corpus(db)
            fact = _make_fact(tenant_id, doc_id, version_id, status="verified")
            db.add(fact)
            await db.flush()
            fact.verified_by_actor_id = actor_id
            await db.flush()

            await bulk_edit_facts(db, tenant_id, [{"fact_id": fact.id, "new_value": {"v": "Corrected"}}], actor_id)

            await db.refresh(fact)
            assert fact.status == "in_review"
            assert fact.verified_by_actor_id is None
        finally:
            await db.rollback()
            await db.close()


@pytest.mark.asyncio
async def test_bulk_edit_facts_skips_noop_edits():
    async with AsyncSessionLocal() as db:
        try:
            tenant_id, actor_id, folder_id, doc_id, version_id = await _make_corpus(db)
            fact = _make_fact(tenant_id, doc_id, version_id, status="machine")
            db.add(fact)
            await db.flush()

            result = await bulk_edit_facts(
                db, tenant_id, [{"fact_id": fact.id, "new_value": {"v": "Test Value"}}], actor_id,
            )
            assert result["changed_count"] == 0
            assert result["rows"][0]["changed"] is False

            await db.refresh(fact)
            assert fact.status == "machine"
        finally:
            await db.rollback()
            await db.close()


@pytest.mark.asyncio
async def test_revert_bulk_edit_batch_restores_value_and_status():
    async with AsyncSessionLocal() as db:
        try:
            tenant_id, actor_id, folder_id, doc_id, version_id = await _make_corpus(db)
            fact = _make_fact(tenant_id, doc_id, version_id, status="machine")
            db.add(fact)
            await db.flush()

            result = await bulk_edit_facts(
                db, tenant_id, [{"fact_id": fact.id, "new_value": {"v": "Corrected"}}], actor_id,
            )
            batch_id = uuid.UUID(result["batch_id"])

            revert_result = await revert_bulk_edit_batch(db, tenant_id, batch_id, actor_id)
            assert str(fact.id) in revert_result["fact_ids"]

            await db.refresh(fact)
            assert fact.value == {"v": "Test Value"}
            assert fact.status == "machine"
        finally:
            await db.rollback()
            await db.close()


@pytest.mark.asyncio
async def test_revert_bulk_edit_batch_unknown_batch_404s():
    async with AsyncSessionLocal() as db:
        try:
            tenant_id, actor_id, folder_id, doc_id, version_id = await _make_corpus(db)
            with pytest.raises(HTTPException) as exc_info:
                await revert_bulk_edit_batch(db, tenant_id, uuid.uuid4(), actor_id)
            assert exc_info.value.status_code == 404
        finally:
            await db.rollback()
            await db.close()


# ── TS4 — field-shape trust signal + stitch-ambiguity resolution ──


@pytest.mark.asyncio
async def test_confirm_fact_records_trust_signal():
    async with AsyncSessionLocal() as db:
        try:
            tenant_id, actor_id, folder_id, doc_id, version_id = await _make_corpus(db)
            field_name = f"ts4_owner_{uuid.uuid4().hex}"
            fact = _make_fact(tenant_id, doc_id, version_id, field_name=field_name)
            db.add(fact)
            await db.flush()

            await confirm_fact(db, tenant_id, fact.id, actor_id)

            signal = await field_trust_service.get_trust_signal(db, field_name)
            assert signal.confirmed_count == 1
        finally:
            await db.rollback()
            await db.close()


@pytest.mark.asyncio
async def test_confirm_fact_does_not_record_trust_signal_for_handwritten():
    async with AsyncSessionLocal() as db:
        try:
            tenant_id, actor_id, folder_id, doc_id, version_id = await _make_corpus(db)
            field_name = f"ts4_handwritten_{uuid.uuid4().hex}"
            fact = _make_fact(tenant_id, doc_id, version_id, field_name=field_name, is_handwritten=True)
            db.add(fact)
            await db.flush()

            await confirm_fact(db, tenant_id, fact.id, actor_id)

            assert await field_trust_service.get_trust_signal(db, field_name) is None
        finally:
            await db.rollback()
            await db.close()


@pytest.mark.asyncio
async def test_bulk_edit_records_correction_for_in_review_fact():
    async with AsyncSessionLocal() as db:
        try:
            tenant_id, actor_id, folder_id, doc_id, version_id = await _make_corpus(db)
            field_name = f"ts4_corrected_{uuid.uuid4().hex}"
            fact = _make_fact(tenant_id, doc_id, version_id, field_name=field_name, status="in_review")
            db.add(fact)
            await db.flush()

            await bulk_edit_facts(db, tenant_id, [{"fact_id": fact.id, "new_value": {"v": "Corrected"}}], actor_id)

            signal = await field_trust_service.get_trust_signal(db, field_name)
            assert signal.corrected_count == 1
            assert signal.confirmed_count == 0
        finally:
            await db.rollback()
            await db.close()


@pytest.mark.asyncio
async def test_bulk_edit_does_not_record_correction_for_machine_fact():
    """Editing a never-reviewed 'machine' fact for the first time isn't a
    correction of a prior human confirmation — only editing something
    already flagged in_review counts."""
    async with AsyncSessionLocal() as db:
        try:
            tenant_id, actor_id, folder_id, doc_id, version_id = await _make_corpus(db)
            field_name = f"ts4_machine_edit_{uuid.uuid4().hex}"
            fact = _make_fact(tenant_id, doc_id, version_id, field_name=field_name, status="machine")
            db.add(fact)
            await db.flush()

            await bulk_edit_facts(db, tenant_id, [{"fact_id": fact.id, "new_value": {"v": "Corrected"}}], actor_id)

            assert await field_trust_service.get_trust_signal(db, field_name) is None
        finally:
            await db.rollback()
            await db.close()


@pytest.mark.asyncio
async def test_adjudication_queue_surfaces_trust_signal():
    async with AsyncSessionLocal() as db:
        try:
            tenant_id, actor_id, folder_id, doc_id, version_id = await _make_corpus(db)
            field_name = f"ts4_queue_{uuid.uuid4().hex}"
            fact = _make_fact(tenant_id, doc_id, version_id, field_name=field_name)
            db.add(fact)
            await db.flush()
            await field_trust_service.record_confirmation(db, field_name)
            await field_trust_service.record_confirmation(db, field_name)
            await field_trust_service.record_correction(db, field_name)

            queue = await get_adjudication_queue(db, tenant_id, category="low_confidence")
            item = next(f for f in queue["facts"] if f["fact_id"] == str(fact.id))
            assert item["trust_signal"] == {"confirmed_count": 2, "corrected_count": 1}
        finally:
            await db.rollback()
            await db.close()


async def _make_stitch_ambiguous_fact(db, tenant_id, doc_id, version_id, shape_hash):
    fact = Fact(
        id=uuid.uuid4(), tenant_id=tenant_id, document_id=doc_id, version_id=version_id,
        field_name="_stitch_ambiguous",
        value={"shape_hash": shape_hash, "page_a": 1, "page_b": 2, "reason": "test"},
        confidence=None, is_handwritten=False, status="in_review",
    )
    db.add(fact)
    await db.flush()
    return fact


@pytest.mark.asyncio
async def test_resolve_stitch_ambiguity_writes_human_shape_decision():
    async with AsyncSessionLocal() as db:
        try:
            tenant_id, actor_id, folder_id, doc_id, version_id = await _make_corpus(db)
            shape_hash = f"ts4_shape_{uuid.uuid4().hex}"
            fact = await _make_stitch_ambiguous_fact(db, tenant_id, doc_id, version_id, shape_hash)

            resolved = await resolve_stitch_ambiguity(db, tenant_id, fact.id, "vertical", actor_id)
            assert resolved.status == "verified"

            decision = await table_shape_service.get_cached_shape_decision(db, shape_hash)
            assert decision.relation == "vertical"
            assert decision.decided_by == "human"
        finally:
            await db.rollback()
            await db.close()


@pytest.mark.asyncio
async def test_resolve_stitch_ambiguity_human_outranks_existing_llm_decision():
    """table_shape_service.record_shape_decision()'s existing precedence
    rule (human always outranks a prior llm guess for the same shape) is
    exercised for real here through the new write path."""
    async with AsyncSessionLocal() as db:
        try:
            tenant_id, actor_id, folder_id, doc_id, version_id = await _make_corpus(db)
            shape_hash = f"ts4_override_{uuid.uuid4().hex}"
            await table_shape_service.record_shape_decision(db, shape_hash, "vertical", decided_by="llm", confidence=0.65)

            fact = await _make_stitch_ambiguous_fact(db, tenant_id, doc_id, version_id, shape_hash)
            await resolve_stitch_ambiguity(db, tenant_id, fact.id, "horizontal", actor_id)

            decision = await table_shape_service.get_cached_shape_decision(db, shape_hash)
            assert decision.relation == "horizontal"
            assert decision.decided_by == "human"
        finally:
            await db.rollback()
            await db.close()


@pytest.mark.asyncio
async def test_resolve_stitch_ambiguity_rejects_invalid_relation():
    async with AsyncSessionLocal() as db:
        try:
            tenant_id, actor_id, folder_id, doc_id, version_id = await _make_corpus(db)
            fact = await _make_stitch_ambiguous_fact(db, tenant_id, doc_id, version_id, f"ts4_bad_{uuid.uuid4().hex}")

            with pytest.raises(HTTPException) as exc_info:
                await resolve_stitch_ambiguity(db, tenant_id, fact.id, "sideways", actor_id)
            assert exc_info.value.status_code == 400
        finally:
            await db.rollback()
            await db.close()


@pytest.mark.asyncio
async def test_resolve_stitch_ambiguity_rejects_wrong_fact_type():
    async with AsyncSessionLocal() as db:
        try:
            tenant_id, actor_id, folder_id, doc_id, version_id = await _make_corpus(db)
            fact = _make_fact(tenant_id, doc_id, version_id)  # a normal low-confidence fact
            db.add(fact)
            await db.flush()

            with pytest.raises(HTTPException) as exc_info:
                await resolve_stitch_ambiguity(db, tenant_id, fact.id, "vertical", actor_id)
            assert exc_info.value.status_code == 409
        finally:
            await db.rollback()
            await db.close()


@pytest.mark.asyncio
async def test_adjudication_queue_stitch_ambiguous_category():
    async with AsyncSessionLocal() as db:
        try:
            tenant_id, actor_id, folder_id, doc_id, version_id = await _make_corpus(db)
            await _make_stitch_ambiguous_fact(db, tenant_id, doc_id, version_id, f"ts4_cat_{uuid.uuid4().hex}")

            queue = await get_adjudication_queue(db, tenant_id, category="stitch_ambiguous")
            assert queue["total"] >= 1
            assert all(f["field_name"] == "_stitch_ambiguous" for f in queue["facts"])
        finally:
            await db.rollback()
            await db.close()
