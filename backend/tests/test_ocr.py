import pytest
from app.ocr.extractor import _extract_image, _extract_pdf
from app.ocr.providers.llamaparse_provider import LlamaParseProvider
from app.pipeline.chunker import TextChunker, Chunk


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
