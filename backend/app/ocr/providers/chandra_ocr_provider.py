import asyncio
from typing import List
from app.ai.base import OCRProvider
from app.ocr.extractor import extract_pages_from_file


class ChandraOCRProvider(OCRProvider):
    """General-purpose OCR via Chandra/Datalab for the search/chat
    full-text pipeline — distinct from ChandraVLMProvider
    (app/ai/providers/chandra_provider.py), which does field-schema-driven
    structured extraction for the Facts pipeline only, and only for
    documents matched to a registered template. This provider is the
    Chandra equivalent of PaddleOCRProvider/tesseract: whole-page plain
    text, no field mapping, used for every scanned/handwritten page
    regardless of template match. Digital-text PDF pages are unaffected —
    Chandra is only invoked as the OCR fallback for pages with no
    extractable text layer, same trigger condition as tesseract/paddle
    (see extractor.py's _extract_pdf/_extract_image)."""

    async def extract_pages(self, file_bytes: bytes, filename: str) -> List[dict]:
        return await asyncio.to_thread(extract_pages_from_file, file_bytes, filename, "chandra")
