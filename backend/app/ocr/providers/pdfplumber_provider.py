import io
import pdfplumber
import asyncio
from typing import List
from app.ai.base import OCRProvider

class PdfPlumberProvider(OCRProvider):
    async def extract_pages(self, file_bytes: bytes, filename: str) -> List[dict]:
        def _extract():
            pages = []
            if filename.lower().endswith(".pdf"):
                with pdfplumber.open(io.BytesIO(file_bytes)) as pdf:
                    for i, page in enumerate(pdf.pages):
                        text = page.extract_text() or ""
                        words = page.extract_words()
                        pages.append({
                            "page_number": i + 1,
                            "text": text,
                            "words": words,
                            "bbox": {"width": page.width, "height": page.height}
                        })
            else:
                pages.append({
                    "page_number": 1,
                    "text": file_bytes.decode('utf-8', errors='ignore'),
                    "words": [],
                    "bbox": {}
                })
            return pages
            
        return await asyncio.to_thread(_extract)
