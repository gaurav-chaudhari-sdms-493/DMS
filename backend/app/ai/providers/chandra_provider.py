"""Chandra (Datalab) VLM provider — real API integration, written from
Datalab's own public documentation (documentation.datalab.to), not ported
from any third party's implementation.

Architectural note: unlike Gemini/OpenRouter, Chandra's /convert endpoint
is a fixed document-to-structure converter, not a general instruction-
following VLM — it does not accept our free-text field-schema prompt
directly. It also has no per-field "extract exactly these named columns"
concept; it returns whichever table structure it detects, as HTML with
per-cell bbox/confidence attributes. So this provider does two things a
plain generateContent-style call doesn't need to:
  1. Recovers the field list from the end of the prompt text (the exact
     JSON array `_build_extraction_prompt()` embeds there) rather than
     forwarding the prompt itself.
  2. Maps Chandra's detected table columns onto that field list by
     column ORDER, since Chandra has no notion of our field names.
     Deliberately the simplest possible mapping for a first cut — no
     printed-column-number convention is assumed, unlike the OCR-first
     project this engine was reviewed against.

Bbox handling (fixed live 2026-09-03 after the first version shipped
with every bbox silently None): request `output_format=json`, not
`html` — the json tree's root block carries the page's own
[0,0,width,height] in Datalab's internal render resolution, which is
NOT the resolution of the image we sent it and is never surfaced any
other way. Every cell's data-bbox (space-separated pixels in that same
resolution) gets divided by that to land in our 0-1 fraction space.

Known, honest limitation: Chandra doesn't give a documented per-field
confidence in the exact 0.0-1.0 shape our schema expects — this maps
Datalab's `data-confidence` attribute through directly when present,
defaulting to a neutral estimate when absent, rather than inventing
false precision.
"""
from __future__ import annotations

import asyncio
import json
import re
from html.parser import HTMLParser
from typing import Any, Dict, List, Optional

import httpx

from app.ai.base import VLMProvider

_BASE_URL = "https://www.datalab.to/api/v1/convert"
_POLL_INTERVAL_S = 3.0
_POLL_TIMEOUT_S = 180.0


def _extract_field_names(prompt: str) -> List[str]:
    """Pulls the field list back out of _build_extraction_prompt()'s
    output — that function always ends the prompt with
    'Field schema:\\n<json array>'. Returns [] (never raises) if the
    prompt doesn't have that shape, so a malformed/foreign prompt
    degrades to no field mapping rather than crashing extraction."""
    marker = "Field schema:\n"
    idx = prompt.rfind(marker)
    if idx == -1:
        return []
    try:
        schema = json.loads(prompt[idx + len(marker):])
        return [f["name"] for f in schema if isinstance(f, dict) and "name" in f]
    except (json.JSONDecodeError, TypeError, KeyError):
        return []


class _TableHTMLParser(HTMLParser):
    """Pulls table rows of (text, bbox, confidence) cells out of Chandra's
    HTML output. Deliberately tolerant: a malformed or missing bbox/
    confidence attribute yields None for that cell rather than raising —
    a partially-useful row beats losing the whole page to one bad cell."""

    def __init__(self) -> None:
        super().__init__()
        self.rows: List[List[Dict[str, Any]]] = []
        self._current_row: Optional[List[Dict[str, Any]]] = None
        self._current_cell: Optional[Dict[str, Any]] = None
        self._cell_text: List[str] = []

    def handle_starttag(self, tag: str, attrs: list) -> None:
        attrs_d = dict(attrs)
        if tag == "tr":
            self._current_row = []
        elif tag in ("td", "th") and self._current_row is not None:
            self._cell_text = []
            self._current_cell = {
                "bbox": _parse_bbox(attrs_d.get("data-bbox")),
                "confidence": _parse_confidence(attrs_d.get("data-confidence")),
            }
        elif tag == "br" and self._current_cell is not None:
            # A multi-line cell's <br/>-separated lines otherwise
            # concatenate with no separator at all ("B-175Akola") — a
            # cell that's genuinely one real newline (e.g. "Shri Juni
            # Masjid," / "Hirapur" / "Tal. Murtizapur") needs a space so
            # it reads as three distinct words, not one run-together one.
            self._cell_text.append(" ")

    def handle_data(self, data: str) -> None:
        if self._current_cell is not None:
            self._cell_text.append(data)

    def handle_endtag(self, tag: str) -> None:
        if tag in ("td", "th") and self._current_cell is not None:
            self._current_cell["text"] = re.sub(r"\s+", " ", "".join(self._cell_text)).strip()
            self._current_row.append(self._current_cell)
            self._current_cell = None
        elif tag == "tr" and self._current_row is not None:
            if self._current_row:
                self.rows.append(self._current_row)
            self._current_row = None


def _parse_bbox(raw: Optional[str]) -> Optional[List[float]]:
    """Real bug found live 2026-09-03: data-bbox is SPACE-separated
    ("50.0 275.6 215.5 961.4"), not comma-separated — the original
    `raw.split(",")` silently produced a 1-element list on every real
    response, which the length-4 check then rejected, so every bbox came
    back None despite Datalab returning real coordinates on every cell."""
    if not raw:
        return None
    try:
        parts = [float(p) for p in raw.split()]
        if len(parts) != 4:
            return None
        # Pixel coordinates in Datalab's own internal render resolution —
        # normalize to our 0-1 fraction space in _normalize_bbox(), once
        # the caller has the page's own bbox to divide by.
        return parts
    except ValueError:
        return None


def _normalize_bbox(bbox: Optional[List[float]], page_w: Optional[float], page_h: Optional[float]) -> Optional[List[float]]:
    """Real bug found live 2026-09-03: Datalab's cell coordinates are
    pixels in ITS OWN internal render resolution, not the resolution of
    the image we sent it (measured: 1540x2184 returned for a 1238x1753
    source image) — dividing by our own image dimensions would have been
    silently wrong. The page's own bbox (from the json tree's root "Page"
    block) is the only place that resolution is ever given to us."""
    if not bbox or not page_w or not page_h:
        return None
    x0, y0, x1, y1 = bbox
    return [x0 / page_w, y0 / page_h, x1 / page_w, y1 / page_h]


def _parse_confidence(raw: Optional[str]) -> Optional[float]:
    if not raw:
        return None
    try:
        v = float(raw)
        return v if 0.0 <= v <= 1.0 else None
    except ValueError:
        return None


class ChandraVLMProvider(VLMProvider):
    name = "chandra"
    model = "datalab-convert/accurate"

    def __init__(self, api_key: str) -> None:
        self.api_key = api_key

    async def extract_structured(self, image_bytes: bytes, prompt: str) -> str:
        field_names = _extract_field_names(prompt)

        async with httpx.AsyncClient(timeout=60.0) as client:
            submit = await client.post(
                _BASE_URL,
                headers={"X-API-Key": self.api_key},
                files={"file": ("page.png", image_bytes, "image/png")},
                # json, not html: Datalab renders each page at its own
                # internal resolution (measured live: 1540x2184 px for a
                # 1238x1753 source image — not tied to the input image
                # size at all), and the html/metadata responses never
                # surface that canvas size anywhere. The json tree's root
                # block (block_type "Page") carries an explicit
                # [0,0,width,height] bbox — the only place that number is
                # available — which is what every cell coordinate below
                # needs to be divided by to land in our 0-1 fraction space.
                data={"output_format": "json", "mode": "accurate", "extras": "table_cell_bboxes"},
            )
            if submit.status_code != 200:
                raise Exception(f"Chandra convert request failed with status {submit.status_code}: {submit.text}")
            check_url = submit.json().get("request_check_url")
            if not check_url:
                raise Exception(f"Chandra convert response missing request_check_url: {submit.text}")

            elapsed = 0.0
            result = None
            while elapsed < _POLL_TIMEOUT_S:
                await asyncio.sleep(_POLL_INTERVAL_S)
                elapsed += _POLL_INTERVAL_S
                poll = await client.get(check_url, headers={"X-API-Key": self.api_key})
                if poll.status_code != 200:
                    raise Exception(f"Chandra status poll failed with status {poll.status_code}: {poll.text}")
                data = poll.json()
                status = data.get("status")
                if status == "complete":
                    result = data
                    break
                if status == "failed":
                    raise Exception(f"Chandra conversion failed: {data.get('error')}")
            if result is None:
                raise Exception(f"Chandra conversion did not complete within {_POLL_TIMEOUT_S}s")

        page_block = ((result.get("json") or {}).get("children") or [{}])[0]
        html = page_block.get("html") or result.get("html") or ""
        page_bbox = page_block.get("bbox")
        page_w, page_h = (float(page_bbox[2]), float(page_bbox[3])) if isinstance(page_bbox, list) and len(page_bbox) == 4 else (None, None)

        parser = _TableHTMLParser()
        parser.feed(html)

        rows_out = []
        for html_row in parser.rows:
            row: Dict[str, Any] = {}
            for i, cell in enumerate(html_row):
                if i >= len(field_names):
                    break  # more detected columns than our schema has fields — code decides, drop the rest rather than guess
                if not cell["text"]:
                    continue
                row[field_names[i]] = {
                    "value": cell["text"],
                    "bbox": _normalize_bbox(cell["bbox"], page_w, page_h),
                    "confidence": cell["confidence"] if cell["confidence"] is not None else 0.5,
                    "is_handwritten": False,
                }
            if row:
                rows_out.append(row)

        return json.dumps({"rows": rows_out, "marginalia": []}, ensure_ascii=False)
