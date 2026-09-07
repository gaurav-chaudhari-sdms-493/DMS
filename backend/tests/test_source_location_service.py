"""T05 — source_location_service.locate_value_in_pages, the piece that
turns a plain LLM-extracted metadata value back into a page + bbox using
the word_regions extractor.py already computes and used to be discarded."""
from app.services.source_location_service import locate_value_in_pages


def _word(text, x0, y0, x1, y1):
    return {"text": text, "x0": x0, "y0": y0, "x1": x1, "y1": y1}


def _page(page_number, text, words):
    return {"page_number": page_number, "text": text, "words": words}


def test_locates_a_single_word_value():
    pages = [_page(1, "Register No. WB-15 issued today", [
        _word("Register", 0.1, 0.1, 0.2, 0.12),
        _word("No.", 0.2, 0.1, 0.24, 0.12),
        _word("WB-15", 0.25, 0.1, 0.32, 0.12),
        _word("issued", 0.33, 0.1, 0.4, 0.12),
        _word("today", 0.41, 0.1, 0.48, 0.12),
    ])]
    result = locate_value_in_pages("WB-15", pages)
    assert result == {"page_number": 1, "x0": 0.25, "y0": 0.1, "x1": 0.32, "y1": 0.12}


def test_locates_a_multi_word_value_and_unions_the_bboxes():
    pages = [_page(1, "Trust Anjuman Jumma Masjid Trust registered 1973", [
        _word("Trust", 0.1, 0.2, 0.15, 0.22),
        _word("Anjuman", 0.16, 0.2, 0.24, 0.22),
        _word("Jumma", 0.25, 0.2, 0.31, 0.22),
        _word("Masjid", 0.32, 0.2, 0.39, 0.22),
        _word("Trust", 0.40, 0.2, 0.46, 0.22),
        _word("registered", 0.47, 0.2, 0.56, 0.22),
        _word("1973", 0.57, 0.2, 0.62, 0.22),
    ])]
    result = locate_value_in_pages("Anjuman Jumma Masjid Trust", pages)
    assert result is not None
    assert result["page_number"] == 1
    assert result["x0"] == 0.16
    assert result["x1"] == 0.46
    assert result["y0"] == 0.2
    assert result["y1"] == 0.22


def test_finds_the_value_on_a_later_page_not_just_the_first():
    pages = [
        _page(1, "Cover page, no serial data here", [_word("Cover", 0.1, 0.1, 0.2, 0.12)]),
        _page(2, "Serial WB-42 recorded", [
            _word("Serial", 0.1, 0.1, 0.18, 0.12),
            _word("WB-42", 0.19, 0.1, 0.26, 0.12),
            _word("recorded", 0.27, 0.1, 0.36, 0.12),
        ]),
    ]
    result = locate_value_in_pages("WB-42", pages)
    assert result is not None
    assert result["page_number"] == 2


def test_returns_none_when_the_value_is_not_on_any_page():
    pages = [_page(1, "This page mentions nothing relevant", [
        _word("This", 0.1, 0.1, 0.15, 0.12),
    ])]
    assert locate_value_in_pages("Completely Unrelated Value", pages) is None


def test_returns_none_for_a_paraphrased_value_not_verbatim_on_the_page():
    """A reformatted date is the classic case: the LLM normalises
    '15/03/2024' on the page into '15 March 2024' in the extracted value --
    there's no verbatim run of words to point at, so no region, not a
    guessed one."""
    pages = [_page(1, "Date of registration: 15/03/2024", [
        _word("Date", 0.1, 0.1, 0.15, 0.12),
        _word("of", 0.16, 0.1, 0.18, 0.12),
        _word("registration:", 0.19, 0.1, 0.32, 0.12),
        _word("15/03/2024", 0.33, 0.1, 0.45, 0.12),
    ])]
    assert locate_value_in_pages("15 March 2024", pages) is None


def test_returns_none_for_a_non_string_value():
    pages = [_page(1, "42", [_word("42", 0.1, 0.1, 0.15, 0.12)])]
    assert locate_value_in_pages(42, pages) is None
    assert locate_value_in_pages(None, pages) is None
    assert locate_value_in_pages({"nested": "dict"}, pages) is None


def test_returns_none_for_a_too_short_value():
    """A single character is too likely to false-positive against
    unrelated boilerplate to be worth a region."""
    pages = [_page(1, "A B C", [_word("A", 0.1, 0.1, 0.12, 0.12)])]
    assert locate_value_in_pages("A", pages) is None


def test_matching_is_case_and_whitespace_insensitive():
    pages = [_page(1, "district   WARDHA gazette", [
        _word("district", 0.1, 0.1, 0.2, 0.12),
        _word("WARDHA", 0.21, 0.1, 0.3, 0.12),
        _word("gazette", 0.31, 0.1, 0.4, 0.12),
    ])]
    result = locate_value_in_pages("wardha", pages)
    assert result is not None
    assert result["x0"] == 0.21


def test_page_with_no_words_is_skipped_even_if_text_matches():
    """A page's `text` came through fine but `words` is empty (e.g. an
    OCR-fallback page that never ran through pdfplumber's extract_words) --
    must not crash, just find no region on that page."""
    pages = [_page(1, "Serial WB-99 recorded", [])]
    assert locate_value_in_pages("WB-99", pages) is None
