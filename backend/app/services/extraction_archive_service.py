"""TS3 — content-hash-keyed archive for raw OCR and VLM responses.

Not tenant-scoped by design: see doc_dg_ocr_archive/doc_dg_vlm_archive's
migration docstring. Every function here is best-effort from the
caller's point of view — a cache miss or a write failure just means
"go do the real OCR/VLM call," never a hard failure, consistent with
this pipeline's existing best-effort conventions (T22/T23/TS1/TS2 all
degrade the same way).
"""
import hashlib
from typing import List, Optional

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.ocr_archive import OCRArchive
from app.models.vlm_archive import VLMArchive


async def get_cached_ocr(db: AsyncSession, content_hash: str, ocr_engine: str) -> Optional[List[dict]]:
    archived = await db.get(OCRArchive, {"content_hash": content_hash, "ocr_engine": ocr_engine})
    return archived.pages if archived else None


async def record_ocr(db: AsyncSession, content_hash: str, ocr_engine: str, pages: List[dict]) -> None:
    existing = await db.get(OCRArchive, {"content_hash": content_hash, "ocr_engine": ocr_engine})
    if existing:
        return
    db.add(OCRArchive(content_hash=content_hash, ocr_engine=ocr_engine, pages=pages))
    await db.flush()


def compute_vlm_cache_key(file_hash: str, page_number: int, prompt: str) -> str:
    canonical = f"{file_hash}:{page_number}:{prompt}"
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


async def get_cached_vlm_response(db: AsyncSession, cache_key: str) -> Optional[str]:
    archived = await db.get(VLMArchive, cache_key)
    return archived.raw_response if archived else None


async def record_vlm_response(db: AsyncSession, cache_key: str, raw_response: str) -> None:
    existing = await db.get(VLMArchive, cache_key)
    if existing:
        return
    db.add(VLMArchive(cache_key=cache_key, raw_response=raw_response))
    await db.flush()
