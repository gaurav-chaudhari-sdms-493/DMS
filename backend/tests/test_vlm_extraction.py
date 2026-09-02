import json

from app.pipeline.vlm_extraction import _parse_vlm_response, _build_extraction_prompt


def test_parse_vlm_response_returns_rows_and_marginalia():
    raw = json.dumps({
        "rows": [{"owner": {"value": "Priya Sharma", "bbox": [0.1, 0.1, 0.5, 0.2], "confidence": 0.9, "is_handwritten": False}}],
        "marginalia": [{"text": "disputed boundary", "bbox": [0.8, 0.9, 0.95, 0.95]}],
    })
    rows, marginalia = _parse_vlm_response(raw)
    assert len(rows) == 1
    assert rows[0]["owner"]["value"] == "Priya Sharma"
    assert len(marginalia) == 1
    assert marginalia[0]["text"] == "disputed boundary"


def test_parse_vlm_response_missing_marginalia_key_defaults_empty():
    raw = json.dumps({"rows": [{"owner": {"value": "X", "bbox": [0, 0, 1, 1], "confidence": 0.5}}]})
    rows, marginalia = _parse_vlm_response(raw)
    assert len(rows) == 1
    assert marginalia == []


def test_parse_vlm_response_strips_markdown_fences():
    raw = "```json\n" + json.dumps({"rows": [], "marginalia": []}) + "\n```"
    rows, marginalia = _parse_vlm_response(raw)
    assert rows == []
    assert marginalia == []


def test_build_extraction_prompt_asks_for_handwritten_and_marginalia():
    prompt = _build_extraction_prompt([{"name": "owner", "type": "string", "required": True}])
    assert "is_handwritten" in prompt
    assert "marginalia" in prompt
