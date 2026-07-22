import io
import json
import os
import asyncio
from typing import List
import pdfplumber
from google.cloud import vision
from google.oauth2 import service_account
from app.ai.base import OCRProvider
from app.config import settings


class GCVProvider(OCRProvider):
    """Google Cloud Vision OCR Provider using DOCUMENT_TEXT_DETECTION."""

    def __init__(self, credentials_json: str = "", credentials_path: str = ""):
        self.credentials_json = credentials_json or settings.google_application_credentials_json
        self.credentials_path = credentials_path or getattr(settings, "google_application_credentials_path", "")

    def _get_client(self) -> vision.ImageAnnotatorClient:
        if self.credentials_json:
            try:
                info = json.loads(self.credentials_json)
                creds = service_account.Credentials.from_service_account_info(info)
                return vision.ImageAnnotatorClient(credentials=creds)
            except Exception:
                pass
        if self.credentials_path and os.path.exists(self.credentials_path):
            creds = service_account.Credentials.from_service_account_file(self.credentials_path)
            return vision.ImageAnnotatorClient(credentials=creds)

        return vision.ImageAnnotatorClient()

    async def extract_pages(self, file_bytes: bytes, filename: str) -> List[dict]:
        def _extract():
            client = self._get_client()
            pages = []

            if filename.lower().endswith(".pdf"):
                with pdfplumber.open(io.BytesIO(file_bytes)) as pdf:
                    for i, page in enumerate(pdf.pages):
                        img = page.to_image(resolution=150).original
                        buf = io.BytesIO()
                        img.save(buf, format="PNG")
                        img_bytes = buf.getvalue()

                        image = vision.Image(content=img_bytes)
                        response = client.document_text_detection(image=image)

                        full_annotation = response.full_text_annotation
                        text = full_annotation.text if full_annotation else ""

                        words = []
                        if full_annotation and full_annotation.pages:
                            for page_anno in full_annotation.pages:
                                for block in page_anno.blocks:
                                    for paragraph in block.paragraphs:
                                        for word in paragraph.words:
                                            w_text = "".join([s.text for s in word.symbols])
                                            words.append({"text": w_text})

                        pages.append({
                            "page_number": i + 1,
                            "text": text,
                            "words": words,
                            "bbox": {"width": page.width, "height": page.height}
                        })
            else:
                image = vision.Image(content=file_bytes)
                response = client.document_text_detection(image=image)

                full_annotation = response.full_text_annotation
                text = full_annotation.text if full_annotation else ""

                words = []
                if full_annotation and full_annotation.pages:
                    for page_anno in full_annotation.pages:
                        for block in page_anno.blocks:
                            for paragraph in block.paragraphs:
                                for word in paragraph.words:
                                    w_text = "".join([s.text for s in word.symbols])
                                    words.append({"text": w_text})

                pages.append({
                    "page_number": 1,
                    "text": text,
                    "words": words,
                    "bbox": {}
                })

            return pages

        return await asyncio.to_thread(_extract)
