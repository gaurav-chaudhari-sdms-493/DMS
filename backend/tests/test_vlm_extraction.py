import json

from app.pipeline.vlm_extraction import _parse_vlm_response, _build_extraction_prompt


def test_parse_vlm_response_returns_rows_and_marginalia():
    raw = json.dumps({
        "rows": [{"owner": {"value": "Priya Sharma", "bbox": [0.1, 0.1, 0.5, 0.2], "confidence": 0.9, "is_handwritten": False}}],
        "marginalia": [{"text": "disputed boundary", "bbox": [0.8, 0.9, 0.95, 0.95]}],
    })
    rows, marginalia, page_header = _parse_vlm_response(raw)
    assert len(rows) == 1
    assert rows[0]["owner"]["value"] == "Priya Sharma"
    assert len(marginalia) == 1
    assert marginalia[0]["text"] == "disputed boundary"
    assert page_header == {}


def test_parse_vlm_response_missing_marginalia_key_defaults_empty():
    raw = json.dumps({"rows": [{"owner": {"value": "X", "bbox": [0, 0, 1, 1], "confidence": 0.5}}]})
    rows, marginalia, page_header = _parse_vlm_response(raw)
    assert len(rows) == 1
    assert marginalia == []
    assert page_header == {}


def test_parse_vlm_response_strips_markdown_fences():
    raw = "```json\n" + json.dumps({"rows": [], "marginalia": []}) + "\n```"
    rows, marginalia, page_header = _parse_vlm_response(raw)
    assert rows == []
    assert marginalia == []
    assert page_header == {}


def test_parse_vlm_response_returns_page_header():
    raw = json.dumps({
        "rows": [{"survey_no": {"value": "175", "bbox": [0.1, 0.3, 0.2, 0.35], "confidence": 0.9}}],
        "page_header": {"village": {"value": "Apti", "bbox": [0.1, 0.02, 0.3, 0.06], "confidence": 0.95, "is_handwritten": False}},
        "marginalia": [],
    })
    rows, marginalia, page_header = _parse_vlm_response(raw)
    assert page_header["village"]["value"] == "Apti"


def test_build_extraction_prompt_asks_for_handwritten_and_marginalia():
    prompt = _build_extraction_prompt([{"name": "owner", "type": "string", "required": True}])
    assert "is_handwritten" in prompt
    assert "marginalia" in prompt


def test_build_extraction_prompt_omits_page_header_contract_when_no_header_fields():
    prompt = _build_extraction_prompt([{"name": "owner", "type": "string", "required": True}])
    assert "page_header" not in prompt


def test_build_extraction_prompt_includes_page_header_contract_and_excludes_it_from_row_schema():
    """village/taluka/district on a 7/12 record are printed once in the
    page header, never inside a row -- role: page_header must ask for
    them in a separate top-level object, not alongside the per-row
    schema, or the model has nowhere correct to source them from and
    falls back to guessing a nearby table cell (the live bug this
    covers: village came back as a row's serial number)."""
    field_schema = [
        {"name": "village", "type": "string", "required": True, "role": "page_header"},
        {"name": "survey_no", "type": "string", "required": True, "role": "serial"},
    ]
    prompt = _build_extraction_prompt(field_schema)
    assert "page_header" in prompt
    assert "printed ONCE" in prompt

    header_schema_block = prompt.split("Page-header field schema")[1].split("Field schema:")[0]
    assert "village" in header_schema_block

    row_schema_block = prompt.split("Field schema:")[-1]
    assert "village" not in row_schema_block
    assert "survey_no" in row_schema_block


def test_build_extraction_prompt_stays_chandra_compatible():
    """Regression guard, live bug 2026-09-04: chandra_provider.py's
    _extract_field_names() recovers the row field list by rfind()-ing the
    exact literal marker "Field schema:\\n" and json.loads()-ing
    EVERYTHING after it -- Chandra's /convert endpoint doesn't consume
    this prompt as instructions at all (see that provider's module
    docstring), it only reads this one trailing JSON array back out.
    Renaming the marker (e.g. to "Field schema (per data row):") or
    appending anything after the JSON array (e.g. a page-header schema
    block) makes Chandra silently receive zero fields and return empty
    rows for every page of every document -- exactly what happened live
    when page_header support was first added. This test exercises the
    real chandra_provider parsing function, not a re-implementation of
    it, so it fails immediately if the prompt's tail shape ever drifts
    from what that function expects again."""
    from app.ai.providers.chandra_provider import _extract_field_names

    field_schema = [
        {"name": "village", "type": "string", "required": True, "role": "page_header"},
        {"name": "taluka", "type": "string", "required": False, "role": "page_header"},
        {"name": "survey_no", "type": "string", "required": True, "role": "serial"},
        {"name": "owner_name", "type": "string", "required": False},
    ]
    prompt = _build_extraction_prompt(field_schema)

    # Chandra must recover exactly the ROW fields, in schema order, with
    # the page_header fields excluded entirely -- a page_header field
    # occupying a column slot would silently shift every real table
    # column's mapping (the live bug this whole feature was added to fix
    # in the first place, just relocated into Chandra's own provider).
    assert _extract_field_names(prompt) == ["survey_no", "owner_name"]


def test_build_extraction_prompt_stays_chandra_compatible_without_header_fields():
    from app.ai.providers.chandra_provider import _extract_field_names

    field_schema = [{"name": "owner_name", "type": "string", "required": False}]
    prompt = _build_extraction_prompt(field_schema)
    assert _extract_field_names(prompt) == ["owner_name"]
