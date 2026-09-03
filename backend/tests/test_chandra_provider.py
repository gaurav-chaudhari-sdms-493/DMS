import json

from app.ai.providers.chandra_provider import (
    _extract_field_names,
    _normalize_bbox,
    _parse_bbox,
    _parse_confidence,
    _TableHTMLParser,
)


def test_extract_field_names_reads_the_embedded_schema():
    prompt = (
        "You are reading one page...\n\n"
        'Field schema:\n[{"name": "sr_no", "type": "string", "required": true}, '
        '{"name": "owner", "type": "string", "required": false}]'
    )
    assert _extract_field_names(prompt) == ["sr_no", "owner"]


def test_extract_field_names_returns_empty_on_foreign_prompt():
    assert _extract_field_names("some unrelated prompt with no schema") == []


def test_parse_bbox_is_space_separated_not_comma():
    """Regression guard for the real bug found live 2026-09-03: Datalab's
    data-bbox attribute is space-separated ("50.0 275.6 215.5 961.4"), and
    a comma-split silently produced a 1-element list that the length-4
    check then rejected — every bbox came back None."""
    assert _parse_bbox("50.0 275.6 215.5 961.4") == [50.0, 275.6, 215.5, 961.4]


def test_parse_bbox_rejects_wrong_shape():
    assert _parse_bbox("1.0 2.0 3.0") is None
    assert _parse_bbox("") is None
    assert _parse_bbox(None) is None


def test_parse_confidence_rejects_out_of_range():
    assert _parse_confidence("0.87") == 0.87
    assert _parse_confidence("1.5") is None
    assert _parse_confidence(None) is None


def test_normalize_bbox_divides_by_the_pages_own_canvas():
    """Regression guard: Datalab's cell pixels are in ITS OWN internal
    render resolution (measured live: 1540x2184 for a 1238x1753 source
    image), never the resolution of the image we sent — dividing by our
    own image dimensions would silently misplace every region."""
    bbox = [50.0, 274.2, 215.5, 361.0]
    result = _normalize_bbox(bbox, page_w=1540.0, page_h=2184.0)
    assert result == [50.0 / 1540.0, 274.2 / 2184.0, 215.5 / 1540.0, 361.0 / 2184.0]
    assert all(0.0 <= v <= 1.0 for v in result)


def test_normalize_bbox_none_without_page_dimensions():
    assert _normalize_bbox([1, 2, 3, 4], None, None) is None
    assert _normalize_bbox(None, 100, 100) is None


def test_table_html_parser_splits_rows_and_cells_with_bbox():
    html = (
        '<table><tr data-bbox="0 0 100 10">'
        '<td data-bbox="50.0 275.6 215.5 361.0" data-confidence="0.92">180.</td>'
        '<td data-bbox="215.5 275.6 522.0 361.0" data-confidence="0.85">Priya</td>'
        "</tr></table>"
    )
    parser = _TableHTMLParser()
    parser.feed(html)
    assert len(parser.rows) == 1
    row = parser.rows[0]
    assert row[0]["text"] == "180."
    assert row[0]["bbox"] == [50.0, 275.6, 215.5, 361.0]
    assert row[0]["confidence"] == 0.92
    assert row[1]["text"] == "Priya"


def test_table_html_parser_inserts_space_across_br_line_breaks():
    """Regression guard: a multi-line cell's <br/>-separated text used to
    concatenate with no separator at all ("B-175Akola") instead of
    reading as distinct words."""
    html = '<table><tr><td data-bbox="0 0 10 10">B-175<br/>Akola</td></tr></table>'
    parser = _TableHTMLParser()
    parser.feed(html)
    assert parser.rows[0][0]["text"] == "B-175 Akola"


def test_table_html_parser_skips_empty_cells():
    html = '<table><tr><td data-bbox="0 0 1 1"></td><td data-bbox="0 0 1 1">x</td></tr></table>'
    parser = _TableHTMLParser()
    parser.feed(html)
    assert len(parser.rows[0]) == 2
    assert parser.rows[0][0]["text"] == ""
    assert parser.rows[0][1]["text"] == "x"
