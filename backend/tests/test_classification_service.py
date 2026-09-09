"""T23 classification -- previously had zero test coverage, which is
part of how a real live bug (see below) went unnoticed: match_template()
silently returned None (== "no template matches") for the vast majority
of real documents once enough templates were registered, because the
underlying reasoning model's hidden thinking tokens ate the whole
max_tokens budget before it could write the visible answer."""
import uuid

import pytest
from unittest.mock import AsyncMock

from app.database import AsyncSessionLocal
from app.models.template import Template
from app.services.classification_service import match_template


async def _make_template(db, form_type, era_label):
    t = Template(
        id=uuid.uuid4(), form_type=form_type, era_label=era_label,
        field_schema=[{"name": "sr_no", "type": "string", "required": False}],
        layout="single_page",
    )
    db.add(t)
    await db.flush()
    return t


@pytest.mark.asyncio
async def test_match_template_live_on_a_real_wakf_gazette_cover_page():
    """Live bug, 2026-09-04: confirmed 3/3 reproductions that a real Wakf
    gazette cover page -- which plainly matches the registered
    "Maharashtra State Wakf Gazette Register -- Form B (Property
    Assessment)" template by name, act, and year -- got silently
    classified as no-match at the old max_tokens=512. Runs against the
    REAL current template list (whatever's registered in this DB today),
    not an isolated fixture -- that's the point: the failure only showed
    up once enough templates existed for the reasoning model's hidden
    thinking to outgrow a tight budget, so a test isolated to 1-2 fake
    templates would never have caught it."""
    cover_text = (
        "BY THE CHIEF EXECUTIVE OFFICER\n"
        "No. 43.---Whereas, the Government of Maharashtra under Section 5 (1) and "
        "Sub-section 3 of Section 4 of Central Wakf Act, 1995 has forwarded list of "
        "Wakfs properties to The Maharashtra State Board of Wakfs, Aurangabad for "
        "publication after scrutiny.\n"
        # Real bug found live 2026-09-09: this used to say "District Washim"
        # -- a district no registered template actually covers (only
        # Aurangabad/1973/spread, Wardha/2004/Form B, and Marathwada-region
        # 1973-74 exist) -- and asserted a match should happen anyway "by
        # name, act, and year" alone. That's the exact false-positive
        # pattern (matching on the issuing office's name/act while ignoring
        # a real district mismatch) that silently misclassified a real
        # document (Pune, 2004) against the Aurangabad/1973/spread template
        # and corrupted its extraction. match_template's prompt was fixed
        # to require the document's own district to agree with a
        # candidate's era_label -- so this fixture now names a district
        # (Wardha) that a real registered template actually covers, keeping
        # this test's real purpose (guard the token-starvation regression)
        # intact without depending on the same false-positive behavior the
        # other fix just removed.
        "List of Wakf properities District Wardha enclosed.\n"
        "M. Y. PATEL, Additional Collector and Chief Executive Officer, "
        "Maharashtra State Board of Wakfs, Aurangabad."
    )
    async with AsyncSessionLocal() as db:
        matched = await match_template(db, cover_text)
        assert matched is not None, (
            "match_template returned no match for a document that plainly "
            "matches a registered Wakf gazette template -- likely the "
            "empty-response-from-token-starvation regression again."
        )
        assert "Wakf" in matched.form_type


@pytest.mark.asyncio
async def test_match_template_retries_past_an_empty_response(monkeypatch):
    """The core fix: an empty first response (token-starved reasoning
    model) must not be taken as a final "no match" -- it must retry."""
    import app.services.classification_service as cs_mod

    async with AsyncSessionLocal() as db:
        try:
            unique = uuid.uuid4().hex[:8]
            template = await _make_template(db, f"Retry Test Form {unique}", "era")

            fake_llm = AsyncMock()
            fake_llm.complete.side_effect = ["", f"Retry Test Form {unique} | era"]
            monkeypatch.setattr(cs_mod, "get_llm_provider", lambda: fake_llm)

            matched = await match_template(db, "some sample text")
            assert matched is not None
            assert matched.id == template.id
            assert fake_llm.complete.call_count == 2
        finally:
            await db.rollback()


@pytest.mark.asyncio
async def test_match_template_gives_up_gracefully_after_all_attempts_empty(monkeypatch):
    """All retries exhausted, still empty -- must return None, not crash,
    matching T23's own best-effort contract."""
    import app.services.classification_service as cs_mod

    async with AsyncSessionLocal() as db:
        try:
            unique = uuid.uuid4().hex[:8]
            await _make_template(db, f"Exhausted Test Form {unique}", "era")

            fake_llm = AsyncMock()
            fake_llm.complete.return_value = ""
            monkeypatch.setattr(cs_mod, "get_llm_provider", lambda: fake_llm)

            matched = await match_template(db, "some sample text")
            assert matched is None
            assert fake_llm.complete.call_count == cs_mod.MATCH_TEMPLATE_ATTEMPTS
        finally:
            await db.rollback()


@pytest.mark.asyncio
async def test_match_template_does_not_trust_a_single_confident_none(monkeypatch):
    """2026-09-07 fix: live sampling found the reasoning model can answer
    a clean, non-empty "NONE" on a document that plainly does match --
    confirmed 1 wrong answer in 4 live calls against the same real
    document. A NONE on the first attempt must not end the loop early;
    a later attempt finding the real match must still win."""
    import app.services.classification_service as cs_mod

    async with AsyncSessionLocal() as db:
        try:
            unique = uuid.uuid4().hex[:8]
            template = await _make_template(db, f"Confident None Form {unique}", "era")

            fake_llm = AsyncMock()
            fake_llm.complete.side_effect = ["NONE", f"Confident None Form {unique} | era"]
            monkeypatch.setattr(cs_mod, "get_llm_provider", lambda: fake_llm)

            matched = await match_template(db, "some sample text")
            assert matched is not None
            assert matched.id == template.id
            assert fake_llm.complete.call_count == 2
        finally:
            await db.rollback()


@pytest.mark.asyncio
async def test_match_template_returns_none_only_after_every_attempt_agrees(monkeypatch):
    """A genuinely unclassified document must still end up None -- but
    only after the full attempt budget was spent confirming it, not on
    the strength of a single NONE."""
    import app.services.classification_service as cs_mod

    async with AsyncSessionLocal() as db:
        try:
            unique = uuid.uuid4().hex[:8]
            await _make_template(db, f"Never Matches Form {unique}", "era")

            fake_llm = AsyncMock()
            fake_llm.complete.return_value = "NONE"
            monkeypatch.setattr(cs_mod, "get_llm_provider", lambda: fake_llm)

            matched = await match_template(db, "some sample text")
            assert matched is None
            assert fake_llm.complete.call_count == cs_mod.MATCH_TEMPLATE_ATTEMPTS
        finally:
            await db.rollback()
