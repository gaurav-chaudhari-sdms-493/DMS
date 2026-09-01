from app.services.page_furniture_service import detect_page_furniture


def _page(page_number, lines):
    return {"page_number": page_number, "text": "\n".join(lines), "extraction_failed": False}


def test_stable_top_header_is_flagged():
    pages = [
        _page(1, ["MAHARASHTRA STATE GAZETTE", "Body text line one.", "Body text line two."]),
        _page(2, ["MAHARASHTRA STATE GAZETTE", "More body content here.", "And more body content."]),
        _page(3, ["MAHARASHTRA STATE GAZETTE", "Even more body text.", "Final body line."]),
    ]
    candidates = detect_page_furniture(pages)
    assert len(candidates) == 1
    assert candidates[0]["text"] == "MAHARASHTRA STATE GAZETTE"
    assert candidates[0]["occurrence_count"] == 3
    assert candidates[0]["zone"] == "top"
    assert candidates[0]["pages"] == [1, 2, 3]


def test_stable_bottom_footer_is_flagged():
    pages = [
        _page(1, ["Body text line one.", "Body text line two.", "Confidential — internal use only"]),
        _page(2, ["More body content here.", "And more body content.", "Confidential — internal use only"]),
        _page(3, ["Even more body text.", "Final body line.", "Confidential — internal use only"]),
    ]
    candidates = detect_page_furniture(pages, min_occurrences=2)
    footer = next(c for c in candidates if c["text"] == "Confidential — internal use only")
    assert footer["zone"] == "bottom"


def test_legitimate_repeated_content_at_varying_depth_is_not_flagged():
    """The real documented failure mode this design avoids: content that
    legitimately repeats (a cause-title) but at an unstable position —
    top of one page, bottom of another — must not be mistaken for a
    stable running header just because each individual occurrence sits
    in a margin zone. It's the SPREAD across occurrences that matters,
    not any single one's position."""
    pages = [
        _page(1, ["CAUSE TITLE: Estate of X", "a", "b", "c"]),  # top (position 0.0)
        _page(2, ["a", "b", "c", "CAUSE TITLE: Estate of X"]),  # bottom (position 1.0)
        _page(3, ["CAUSE TITLE: Estate of X", "a", "b", "c"]),  # top again (position 0.0)
    ]
    candidates = detect_page_furniture(pages)
    assert not any(c["text"] == "CAUSE TITLE: Estate of X" for c in candidates)


def test_below_min_occurrences_not_flagged():
    pages = [
        _page(1, ["RUNNING HEADER", "body"]),
        _page(2, ["RUNNING HEADER", "body"]),
    ]
    candidates = detect_page_furniture(pages, min_occurrences=3)
    assert candidates == []


def test_body_content_never_considered_regardless_of_repetition():
    """A repeated line sitting in the MIDDLE of every page (not the
    margin) is never a header/footer candidate, no matter how often it
    repeats — position, not just repetition, gates consideration at all."""
    pages = [
        _page(1, ["top", "a", "b", "REPEATED MIDDLE LINE", "c", "d", "bottom"]),
        _page(2, ["top", "a", "b", "REPEATED MIDDLE LINE", "c", "d", "bottom"]),
        _page(3, ["top", "a", "b", "REPEATED MIDDLE LINE", "c", "d", "bottom"]),
    ]
    candidates = detect_page_furniture(pages)
    assert not any(c["text"] == "REPEATED MIDDLE LINE" for c in candidates)


def test_short_lines_excluded_as_noise():
    pages = [_page(i, ["Hi", "body text here"]) for i in range(1, 4)]
    candidates = detect_page_furniture(pages)
    assert not any(c["text"] == "Hi" for c in candidates)


def test_extraction_failed_pages_skipped():
    pages = [
        {"page_number": 1, "text": "HEADER\nbody", "extraction_failed": False},
        {"page_number": 2, "text": "HEADER\nbody", "extraction_failed": True},
        {"page_number": 3, "text": "HEADER\nbody", "extraction_failed": False},
    ]
    candidates = detect_page_furniture(pages, min_occurrences=2)
    header = next(c for c in candidates if c["text"] == "HEADER")
    assert header["occurrence_count"] == 2
    assert 2 not in header["pages"]


def test_matching_is_case_and_whitespace_insensitive():
    pages = [
        _page(1, ["Running   Header", "middle a", "middle b", "middle c", f"page 1 footer"]),
        _page(2, ["running header", "middle a", "middle b", "middle c", f"page 2 footer"]),
        _page(3, ["RUNNING HEADER", "middle a", "middle b", "middle c", f"page 3 footer"]),
    ]
    candidates = detect_page_furniture(pages)
    assert len(candidates) == 1
    assert candidates[0]["occurrence_count"] == 3


def test_empty_pages_return_no_candidates():
    assert detect_page_furniture([]) == []


def test_within_page_repetition_never_counts_as_furniture():
    """Real bug found against the actual 1973 gazette register: a ditto
    mark ("Do.") repeating many times as separate table-cell lines
    WITHIN one page was being counted as 13 "occurrences" and flagged as
    a furniture candidate. A running header/footer means recurring
    across SEPARATE pages — repeats within a single page (e.g. a
    table's own repeated cell content) must never count, no matter how
    many times or how consistently positioned."""
    lines = ["Do."] * 20  # all sit in the top/bottom margin somewhere by sheer count
    pages = [{"page_number": 1, "text": "\n".join(lines), "extraction_failed": False}]
    candidates = detect_page_furniture(pages, min_occurrences=3)
    assert candidates == []
