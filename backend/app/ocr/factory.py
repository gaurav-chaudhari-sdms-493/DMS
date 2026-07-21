from app.config import settings
from app.ai.base import OCRProvider

_ocr_provider: OCRProvider | None = None

def get_ocr_provider() -> OCRProvider:
    global _ocr_provider
    if _ocr_provider is None:
        if settings.ai_ocr_provider == "pdfplumber":
            from app.ocr.providers.pdfplumber_provider import PdfPlumberProvider
            _ocr_provider = PdfPlumberProvider()
        elif settings.ai_ocr_provider == "llamaparse":
            from app.ocr.providers.llamaparse_provider import LlamaParseProvider
            _ocr_provider = LlamaParseProvider(api_key=settings.llamaparse_api_key)
        elif settings.ai_ocr_provider == "gcv":
            from app.ocr.providers.gcv_provider import GCVProvider
            _ocr_provider = GCVProvider(
                credentials_json=settings.google_application_credentials_json,
                credentials_path=getattr(settings, "google_application_credentials_path", ""),
            )
        else:
            raise ValueError(f"Unknown OCR provider: {settings.ai_ocr_provider}")
    return _ocr_provider
