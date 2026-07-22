import io
import pdfplumber
import asyncio
from typing import List
from app.ai.base import OCRProvider
from app.ocr.exceptions import OCRFallbackRequired


class PdfPlumberProvider(OCRProvider):
    """PDF text extractor using pdfplumber.

    Raises OCRFallbackRequired if a page contains zero or near-zero text,
    or if a PDF cannot be parsed directly, signaling a scanned/image-based
    document that requires an actual OCR provider.
    """

    def __init__(self, min_text_threshold: int = 10):
        self.min_text_threshold = min_text_threshold

    async def extract_pages(self, file_bytes: bytes, filename: str) -> List[dict]:
        def _extract():
            pages = []
            if filename.lower().endswith(".pdf"):
                try:
                    with pdfplumber.open(io.BytesIO(file_bytes)) as pdf:
                        for i, page in enumerate(pdf.pages):
                            text = page.extract_text() or ""
                            if len(text.strip()) < self.min_text_threshold:
                                raise OCRFallbackRequired(
                                    f"Scanned/image-based PDF detected on page {i + 1} — configure AI_OCR_PROVIDER=llamaparse or gcv for this document type"
                                )
                            words = page.extract_words()
                            pages.append({
                                "page_number": i + 1,
                                "text": text,
                                "words": words,
                                "bbox": {"width": page.width, "height": page.height}
                            })
                except OCRFallbackRequired:
                    raise
                except Exception as e:
                    raise OCRFallbackRequired(
                        f"Scanned/image-based PDF detected — configure AI_OCR_PROVIDER=llamaparse or gcv for this document type ({e})"
                    )
            else:
                raw_text = file_bytes.decode("utf-8", errors="ignore")
                if len(raw_text.strip()) < self.min_text_threshold:
                    raise OCRFallbackRequired(
                        "Scanned/image-based document detected — configure AI_OCR_PROVIDER=llamaparse or gcv for this document type"
                    )
                pages.append({
                    "page_number": 1,
                    "text": raw_text,
                    "words": [],
                    "bbox": {}
                })
            return pages

        return await asyncio.to_thread(_extract)
