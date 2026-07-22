class OCRFallbackRequired(Exception):
    """Raised when a non-OCR provider encounters a scanned or image-based document page."""
    pass
