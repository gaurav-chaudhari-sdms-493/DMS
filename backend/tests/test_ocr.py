import io

import pytest
from PIL import Image, ImageDraw

from app.ocr.extractor import _extract_image, _extract_pdf, extract_pages_from_file
from app.ocr.providers.llamaparse_provider import LlamaParseProvider
from app.pipeline.chunker import TextChunker, Chunk
from app.services.source_location_service import locate_value_in_pages


def _image_only_pdf_bytes(lines: list[str]) -> bytes:
    """A one-page PDF with no text layer at all -- an embedded raster image
    only, the same shape as a real scanned register page. Exercises
    extractor.py's `if not text.strip()` OCR-fallback branch in
    _extract_pdf, not the native pdfplumber.extract_words() path."""
    img = Image.new("RGB", (1200, 400), "white")
    d = ImageDraw.Draw(img)
    for i, line in enumerate(lines):
        d.text((60, 80 + i * 80), line, fill="black")
    buf = io.BytesIO()
    img.convert("RGB").save(buf, format="PDF")
    return buf.getvalue()


def test_failed_ocr_sets_extraction_failed_flag():
    """T33 / Section 15 defect test — failed image OCR must set extraction_failed=True."""
    # Blank 1x1 image bytes
    blank_png = b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x06\x00\x00\x00\x1f\x15c4\x00\x00\x00\rIDATx\x9cc\xf8\xff\xff?\x03\x00\x05\xfe\x02\xfe\xa7\x9a\x9a\x00\x00\x00\x00IEND\xaeB`\x82"
    pages = _extract_image(blank_png, "blank_test.png")
    
    assert len(pages) == 1
    assert pages[0]["extraction_failed"] is True


def test_chunker_skips_failed_ocr_pages():
    """TextChunker must not produce text chunks from pages marked with extraction_failed=True."""
    chunker = TextChunker(chunk_size=512, chunk_overlap=64)
    failed_pages = [
        {
            "page_number": 1,
            "text": "Image document: unreadable.png",
            "words": [],
            "bbox": {},
            "extraction_failed": True
        }
    ]
    chunks = chunker.chunk_pages(failed_pages)
    assert len(chunks) == 0


def test_chunker_processes_successful_pages_only():
    """TextChunker must process valid pages while skipping failed ones."""
    chunker = TextChunker(chunk_size=512, chunk_overlap=64)
    mixed_pages = [
        {
            "page_number": 1,
            "text": "Valid extracted land record text for survey number 121.",
            "words": [],
            "bbox": {},
            "extraction_failed": False
        },
        {
            "page_number": 2,
            "text": "Scanned page 2 of document test.pdf",
            "words": [],
            "bbox": {},
            "extraction_failed": True
        }
    ]
    chunks = chunker.chunk_pages(mixed_pages)
    assert len(chunks) == 1
    assert chunks[0].page_number == 1
    assert "survey number 121" in chunks[0].content


def test_scanned_pdf_page_gets_real_word_regions_via_tesseract():
    """T05 (scanned-corpus coverage) -- a PDF page with no text layer at
    all used to fall back to OCR for plain text only, leaving `words`
    empty forever (pdfplumber's extract_words() finds nothing on a page
    with no text layer, and the old OCR fallback only ever called
    image_to_string). It must now carry real per-word regions too, the
    same way a native-text PDF page already did."""
    pdf_bytes = _image_only_pdf_bytes(["Mutawalli: Abdul Karim Sheikh"])
    pages = _extract_pdf(pdf_bytes, "scanned_register.pdf", ocr_engine="tesseract")

    assert len(pages) == 1
    page = pages[0]
    assert page["extraction_failed"] is False
    assert len(page["words"]) > 0
    assert all({"text", "x0", "y0", "x1", "y1"} <= w.keys() for w in page["words"])
    # T06's coordinate contract -- normalised 0-1 page fractions.
    assert all(0.0 <= w["x0"] <= w["x1"] <= 1.0 for w in page["words"])
    assert all(0.0 <= w["y0"] <= w["y1"] <= 1.0 for w in page["words"])


def test_scanned_pdf_word_regions_are_actually_locatable_end_to_end():
    """The real point of T05: a value the pipeline extracted from a
    scanned page can now be traced back to a real region on it, not just
    a page number -- exercised through the same locate_value_in_pages
    the worker calls on every non-VLM metadata value."""
    pdf_bytes = _image_only_pdf_bytes(["Village: Basmath", "Area: 2 hectare 15 are"])
    pages = extract_pages_from_file(pdf_bytes, "scanned_register.pdf", ocr_engine="tesseract")

    location = locate_value_in_pages("Basmath", pages)
    assert location is not None
    assert location["page_number"] == 1
    assert 0.0 <= location["x0"] < location["x1"] <= 1.0


def test_scanned_pdf_page_gets_real_word_regions_via_paddle():
    """Same coverage fix, PaddleOCR engine (T21's Marathi/Devanagari path)
    -- return_word_box=True gives real per-word boxes there too, not just
    with tesseract."""
    pdf_bytes = _image_only_pdf_bytes(["Mutawalli: Abdul Karim Sheikh"])
    pages = _extract_pdf(pdf_bytes, "scanned_register.pdf", ocr_engine="paddle")

    assert len(pages) == 1
    page = pages[0]
    assert page["extraction_failed"] is False
    assert len(page["words"]) > 0
    assert all(0.0 <= w["x0"] <= w["x1"] <= 1.0 for w in page["words"])


def test_extract_image_populates_words_and_bbox_for_a_readable_image():
    """A standalone scanned image upload (not a PDF) gets the same
    treatment -- real per-word regions and real pixel bbox dimensions,
    where before this fix both were always empty for every image."""
    img = Image.new("RGB", (500, 200), "white")
    d = ImageDraw.Draw(img)
    d.text((30, 80), "Survey No. 121", fill="black")
    buf = io.BytesIO()
    img.save(buf, format="PNG")

    pages = _extract_image(buf.getvalue(), "photo.png", ocr_engine="tesseract")
    page = pages[0]
    assert page["extraction_failed"] is False
    assert page["bbox"] == {"width": 500.0, "height": 200.0}
    assert len(page["words"]) > 0
