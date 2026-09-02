import uuid

import pytest

from app.database import AsyncSessionLocal
from app.services.extraction_archive_service import (
    get_cached_ocr, record_ocr, compute_vlm_cache_key,
    get_cached_vlm_response, record_vlm_response, overwrite_vlm_response,
)


@pytest.mark.asyncio
async def test_ocr_cache_miss_returns_none():
    async with AsyncSessionLocal() as db:
        result = await get_cached_ocr(db, "nonexistent_hash_12345", "pdfplumber")
        assert result is None


@pytest.mark.asyncio
async def test_ocr_cache_round_trip():
    async with AsyncSessionLocal() as db:
        try:
            content_hash = f"test_hash_ocr_roundtrip_{uuid.uuid4().hex}"
            pages = [{"page_number": 1, "text": "hello world", "extraction_failed": False}]
            await record_ocr(db, content_hash, "pdfplumber", pages)
            await db.commit()

            cached = await get_cached_ocr(db, content_hash, "pdfplumber")
            assert cached == pages
        finally:
            await db.rollback()


@pytest.mark.asyncio
async def test_ocr_cache_scoped_by_engine():
    """Switching AI_OCR_PROVIDER must never serve a different engine's
    cached result for the same file content."""
    async with AsyncSessionLocal() as db:
        try:
            content_hash = f"test_hash_engine_scope_{uuid.uuid4().hex}"
            await record_ocr(db, content_hash, "pdfplumber", [{"text": "from pdfplumber"}])
            await db.commit()

            cached_paddle = await get_cached_ocr(db, content_hash, "paddleocr")
            assert cached_paddle is None
            cached_pdfplumber = await get_cached_ocr(db, content_hash, "pdfplumber")
            assert cached_pdfplumber == [{"text": "from pdfplumber"}]
        finally:
            await db.rollback()


@pytest.mark.asyncio
async def test_ocr_cache_write_idempotent_first_write_wins():
    async with AsyncSessionLocal() as db:
        try:
            content_hash = f"test_hash_idempotent_{uuid.uuid4().hex}"
            await record_ocr(db, content_hash, "pdfplumber", [{"text": "first"}])
            await record_ocr(db, content_hash, "pdfplumber", [{"text": "second — should be ignored"}])
            await db.commit()

            cached = await get_cached_ocr(db, content_hash, "pdfplumber")
            assert cached == [{"text": "first"}]
        finally:
            await db.rollback()


def test_vlm_cache_key_deterministic():
    k1 = compute_vlm_cache_key("filehash1", 1, "prompt text")
    k2 = compute_vlm_cache_key("filehash1", 1, "prompt text")
    assert k1 == k2


def test_vlm_cache_key_varies_by_page_number():
    k1 = compute_vlm_cache_key("filehash1", 1, "prompt text")
    k2 = compute_vlm_cache_key("filehash1", 2, "prompt text")
    assert k1 != k2


def test_vlm_cache_key_varies_by_prompt():
    """A template's field_schema changing (or a spread's left vs right
    half) must produce a different prompt and therefore a different key
    -- never silently reuse a stale extraction."""
    k1 = compute_vlm_cache_key("filehash1", 1, "prompt asking for field A")
    k2 = compute_vlm_cache_key("filehash1", 1, "prompt asking for field B")
    assert k1 != k2


def test_vlm_cache_key_varies_by_file_hash():
    k1 = compute_vlm_cache_key("filehash1", 1, "prompt text")
    k2 = compute_vlm_cache_key("filehash2", 1, "prompt text")
    assert k1 != k2


@pytest.mark.asyncio
async def test_vlm_cache_round_trip():
    async with AsyncSessionLocal() as db:
        try:
            # Unique per run: doc_dg_vlm_archive rows persist across test
            # runs against this shared dev DB, so a hardcoded key would
            # find an earlier run's committed row already present.
            key = compute_vlm_cache_key(f"test_vlm_roundtrip_{uuid.uuid4().hex}", 1, "a prompt")
            assert await get_cached_vlm_response(db, key) is None

            await record_vlm_response(db, key, '{"rows": [], "marginalia": []}')
            await db.commit()

            cached = await get_cached_vlm_response(db, key)
            assert cached == '{"rows": [], "marginalia": []}'
        finally:
            await db.rollback()


@pytest.mark.asyncio
async def test_vlm_cache_write_once_ignores_a_second_record_call():
    """record_vlm_response is intentionally write-once -- the first
    response for a key wins, a second call is a silent no-op. This is
    exactly why the VLM parse-retry path (vlm_extraction.py) needs
    overwrite_vlm_response instead, tested below."""
    async with AsyncSessionLocal() as db:
        try:
            key = compute_vlm_cache_key(f"test_vlm_writeonce_{uuid.uuid4().hex}", 1, "a prompt")
            await record_vlm_response(db, key, "first response")
            await record_vlm_response(db, key, "second response")
            await db.commit()

            assert await get_cached_vlm_response(db, key) == "first response"
        finally:
            await db.rollback()


@pytest.mark.asyncio
async def test_overwrite_vlm_response_replaces_an_existing_entry():
    async with AsyncSessionLocal() as db:
        try:
            key = compute_vlm_cache_key(f"test_vlm_overwrite_{uuid.uuid4().hex}", 1, "a prompt")
            await record_vlm_response(db, key, "bad malformed response")
            await db.commit()

            await overwrite_vlm_response(db, key, "corrected response")
            await db.commit()

            assert await get_cached_vlm_response(db, key) == "corrected response"
        finally:
            await db.rollback()


@pytest.mark.asyncio
async def test_overwrite_vlm_response_writes_fresh_key_like_record():
    async with AsyncSessionLocal() as db:
        try:
            key = compute_vlm_cache_key(f"test_vlm_overwrite_fresh_{uuid.uuid4().hex}", 1, "a prompt")
            assert await get_cached_vlm_response(db, key) is None

            await overwrite_vlm_response(db, key, "first-ever response")
            await db.commit()

            assert await get_cached_vlm_response(db, key) == "first-ever response"
        finally:
            await db.rollback()
