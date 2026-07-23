import asyncio
from typing import List
from app.ai.base import OCRProvider
from app.ocr.extractor import extract_pages_from_file

class PdfPlumberProvider(OCRProvider):
    async def extract_pages(self, file_bytes: bytes, filename: str) -> List[dict]:
        return await asyncio.to_thread(extract_pages_from_file, file_bytes, filename)

