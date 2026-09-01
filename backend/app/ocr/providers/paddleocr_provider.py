import asyncio
from typing import List
from app.ai.base import OCRProvider
from app.ocr.extractor import extract_pages_from_file


class PaddleOCRProvider(OCRProvider):
    """T90 — local, genuinely-CPU-runnable OCR with real Devanagari
    (Marathi/Hindi) support via PaddleOCR's devanagari_PP-OCRv5 model,
    Apache-2.0 licensed (no legal review gate, unlike Surya/D-6). Live-
    verified against a rendered Marathi test image: extracted text
    matched the source near-exactly (village name "वाशिम" extracted
    perfectly; minor diacritic differences elsewhere, typical OCR
    variance, not a functional failure).

    Model weights (~10s worth of small model files) download on first
    use and are cached under /root/.paddlex/official_models — no network
    access needed on subsequent calls, which matters for the air-gapped
    profile (T91): this provider makes no external API call, so
    enforce_local() doesn't gate it, same as pdfplumber."""

    async def extract_pages(self, file_bytes: bytes, filename: str) -> List[dict]:
        return await asyncio.to_thread(extract_pages_from_file, file_bytes, filename, "paddle")
