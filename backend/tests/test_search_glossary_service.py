import pytest

from app.database import AsyncSessionLocal
from app.services.search_glossary_service import expand_query_terms, _tokenize_words


def test_tokenize_words_lowercases_and_handles_devanagari():
    words = _tokenize_words("Find WAQF records for वक्फ")
    assert words == ["find", "waqf", "records", "for", "वक्फ"]


@pytest.mark.asyncio
async def test_single_word_english_term_expands_to_synonyms():
    async with AsyncSessionLocal() as db:
        terms = await expand_query_terms(db, "find wakf documents")
        assert "waqf" in terms
        assert "वक्फ" in terms
        assert "wakf" not in terms  # never returns the term already in the query


@pytest.mark.asyncio
async def test_devanagari_term_expands_to_latin_synonyms():
    async with AsyncSessionLocal() as db:
        terms = await expand_query_terms(db, "वक्फ नोंदणी शोधा")
        assert "waqf" in terms
        assert "wakf" in terms
        assert "वक्फ" not in terms


@pytest.mark.asyncio
async def test_two_word_phrase_term_matches():
    async with AsyncSessionLocal() as db:
        terms = await expand_query_terms(db, "what is the survey number for this plot")
        assert "सर्वे नंबर" in terms
        assert "s no" in terms


@pytest.mark.asyncio
async def test_multiple_glossary_terms_in_one_query():
    async with AsyncSessionLocal() as db:
        terms = await expand_query_terms(db, "graveyard mutawalli details")
        assert "kabrastan" in terms
        assert "कब्रस्तान" in terms
        assert "मुतवली" in terms


@pytest.mark.asyncio
async def test_no_glossary_match_returns_empty_list():
    async with AsyncSessionLocal() as db:
        terms = await expand_query_terms(db, "completely unrelated financial budget report")
        assert terms == []


@pytest.mark.asyncio
async def test_empty_query_returns_empty_list():
    async with AsyncSessionLocal() as db:
        assert await expand_query_terms(db, "") == []


@pytest.mark.asyncio
async def test_case_insensitive_matching():
    async with AsyncSessionLocal() as db:
        terms_lower = await expand_query_terms(db, "wakf")
        terms_upper = await expand_query_terms(db, "WAKF")
        terms_mixed = await expand_query_terms(db, "WaKf")
        assert terms_lower == terms_upper == terms_mixed
        assert "waqf" in terms_lower
