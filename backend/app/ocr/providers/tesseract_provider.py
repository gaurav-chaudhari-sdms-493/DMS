import io
import asyncio
from typing import List
from app.ai.base import OCRProvider
import logging

logger = logging.getLogger(__name__)

class TesseractOCRProvider(OCRProvider):
    def __init__(self, tesseract_cmd: str | None = None):
        self.tesseract_cmd = tesseract_cmd

    async def extract_pages(self, file_bytes: bytes, filename: str) -> List[dict]:
        def _extract():
            try:
                import pytesseract
                from PIL import Image
                if self.tesseract_cmd:
                    pytesseract.pytesseract.tesseract_cmd = self.tesseract_cmd
            except ImportError as e:
                logger.error("pytesseract or PIL is not installed. Please run `pip install pytesseract pillow`.")
                raise e

            pages = []
            fn = filename.lower()

            if fn.endswith(".pdf"):
                try:
                    from pdf2image import convert_from_bytes
                    images = convert_from_bytes(file_bytes)
                    for i, img in enumerate(images):
                        text = pytesseract.image_to_string(img)
                        pages.append({
                            "page_number": i + 1,
                            "text": text,
                            "words": [],
                            "bbox": {"width": img.width, "height": img.height}
                        })
                except Exception as e:
                    logger.error(f"Failed to process PDF via pdf2image/tesseract: {e}")
                    raise e
            elif fn.endswith((".png", ".jpg", ".jpeg", ".tiff", ".bmp")):
                img = Image.open(io.BytesIO(file_bytes))
                text = pytesseract.image_to_string(img)
                pages.append({
                    "page_number": 1,
                    "text": text,
                    "words": [],
                    "bbox": {"width": img.width, "height": img.height}
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
