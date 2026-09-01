"""TS8 — OCR engine comparison / bake-off harness.

Structured, ground-truth-free scoring of the local OCR engines this
pipeline already offers as interchangeable providers (T90): pdfplumber's
native text layer, Tesseract, and PaddleOCR. Meant to inform
AI_OCR_PROVIDER defaults per document type/language instead of the
current single hardcoded choice — never applied automatically, since
that's the same kind of standing configuration decision D-4 (accuracy
tolerance) already treats as needing a human, not a heuristic.

Adapted from the backlog item's literal wording ("cell-bbox coverage")
to what these engines actually expose: none of the three produce real
table-cell/row structure — PaddleOCR detects text at line granularity,
Tesseract and pdfplumber's own extract_words() at word granularity,
each with one bounding box per detected unit. There is also no labeled
ground-truth corpus for this project's real waqf registers (A1 — the
same constraint already blocking T25/T31/T32), so precision/recall
against a known-correct row count isn't computable here. This harness
scores real, inspectable proxies instead: how much of the page was
actually read (char/line volume), how much of that is the script this
product's stated priority is reading correctly (Devanagari), a
row-likeness heuristic shaped for this project's own numeric
multi-column gazette tables, and the literal >90%-empty-cell degenerate
detector from the backlog item.

A real, confirmed finding from building this: PaddleOCR's predict()
already returns rec_boxes (a bounding box per detected line) and
Tesseract's image_to_data() already returns a bounding box per word,
but neither is captured anywhere in this pipeline today —
extractor.py's _paddle_ocr_image() reads only rec_texts, and the
tesseract path calls image_to_string() rather than image_to_data(),
throwing away position data both libraries already compute. This
harness calls the same underlying libraries directly with their
structured APIs to measure what each engine can actually provide, not
what today's wiring happens to keep — wiring that data into real Facts
would be its own feature (T06 fact regions already exist for VLM
output), out of scope for a comparison harness.
"""
import re
from typing import Any, Dict, List

_DEVANAGARI_RE = re.compile(r"[ऀ-ॿ]")
_PLACEHOLDER_CELLS = {"", ".", "..", "-", "—", "do", "do."}


def _split_pseudo_cells(line: str) -> List[str]:
    return [c.strip() for c in re.split(r"\s{2,}|\|", line)]


def score_text(text: str, engine: str) -> Dict[str, Any]:
    """Ground-truth-free proxies: how much was read, how much of it is
    the script this document actually uses, a row-likeness count tuned
    to a numeric multi-column gazette table, and the literal >90%-empty
    degenerate-table detector."""
    lines = [l for l in text.splitlines() if l.strip()]
    devanagari_chars = len(_DEVANAGARI_RE.findall(text))

    row_like = 0
    total_cells = 0
    empty_cells = 0
    for line in lines:
        cells = [c for c in _split_pseudo_cells(line) if c != ""]
        if len(cells) >= 2 and any(re.search(r"\d", c) for c in cells):
            row_like += 1
        for c in cells:
            total_cells += 1
            if c.lower() in _PLACEHOLDER_CELLS:
                empty_cells += 1

    empty_ratio = (empty_cells / total_cells) if total_cells else 0.0

    return {
        "engine": engine,
        "char_count": len(text),
        "line_count": len(lines),
        "devanagari_char_ratio": round(devanagari_chars / len(text), 4) if text else 0.0,
        "row_like_line_count": row_like,
        "pseudo_cell_count": total_cells,
        "empty_pseudo_cell_ratio": round(empty_ratio, 4),
        "is_degenerate_table": total_cells > 0 and empty_ratio > 0.90,
    }


def score_bbox_units(units: List[Dict[str, Any]], engine: str, granularity: str) -> Dict[str, Any]:
    """units: [{"text": str, "bbox": dict | None}]. granularity is
    'word' (pdfplumber/tesseract) or 'line' (PaddleOCR) — the two
    engines' units aren't the same size, so granularity is recorded
    alongside the count rather than silently averaged together."""
    with_bbox = sum(1 for u in units if u.get("bbox"))
    return {
        "engine": engine,
        "granularity": granularity,
        "unit_count": len(units),
        "units_with_bbox": with_bbox,
        "bbox_coverage": round(with_bbox / len(units), 4) if units else 0.0,
    }


def run_pdfplumber_native(page) -> Dict[str, Any]:
    """page: a pdfplumber Page. Its own native text-layer extraction —
    real per-word bboxes when a text layer exists, empty on a scanned
    page (nothing to extract, not a failure of this engine specifically)."""
    text = page.extract_text() or ""
    raw_words = page.extract_words() or []
    words = [
        {"text": w["text"], "bbox": {"x0": w["x0"], "x1": w["x1"], "top": w["top"], "bottom": w["bottom"]}}
        for w in raw_words
    ]
    return {
        "engine": "pdfplumber_native",
        "text": text,
        "text_score": score_text(text, "pdfplumber_native"),
        "bbox_score": score_bbox_units(words, "pdfplumber_native", "word"),
    }


def run_tesseract(pil_img, lang: str = "eng+hin+mar") -> Dict[str, Any]:
    import pytesseract
    from pytesseract import Output

    data = pytesseract.image_to_data(pil_img, lang=lang, output_type=Output.DICT)
    n = len(data["text"])
    lines: Dict[tuple, List[str]] = {}
    units = []
    for i in range(n):
        t = (data["text"][i] or "").strip()
        if not t:
            continue
        key = (data["block_num"][i], data["par_num"][i], data["line_num"][i])
        lines.setdefault(key, []).append(t)
        units.append({
            "text": t,
            "bbox": {
                "x0": data["left"][i], "y0": data["top"][i],
                "x1": data["left"][i] + data["width"][i], "y1": data["top"][i] + data["height"][i],
            },
        })
    text = "\n".join(" ".join(v) for v in lines.values())
    return {
        "engine": "tesseract",
        "text": text,
        "text_score": score_text(text, "tesseract"),
        "bbox_score": score_bbox_units(units, "tesseract", "word"),
    }


def run_paddleocr(pil_img) -> Dict[str, Any]:
    import numpy as np
    from app.ocr.extractor import _get_paddle_ocr

    ocr = _get_paddle_ocr()
    arr = np.array(pil_img.convert("RGB"))
    texts: List[str] = []
    units = []
    for res in ocr.predict(arr):
        rec_texts = res.get("rec_texts", []) or []
        rec_boxes = res.get("rec_boxes")
        texts.extend(rec_texts)
        for i, t in enumerate(rec_texts):
            bbox = None
            if rec_boxes is not None and i < len(rec_boxes):
                x0, y0, x1, y1 = [float(v) for v in rec_boxes[i]]
                bbox = {"x0": x0, "y0": y0, "x1": x1, "y1": y1}
            units.append({"text": t, "bbox": bbox})
    text = "\n".join(texts)
    return {
        "engine": "paddleocr",
        "text": text,
        "text_score": score_text(text, "paddleocr"),
        "bbox_score": score_bbox_units(units, "paddleocr", "line"),
    }


def recommend(results: Dict[str, Any]) -> Dict[str, Any]:
    """Decision-support only — never applied to AI_OCR_PROVIDER
    automatically, same standing-config-needs-a-human posture as D-4.
    Picks the engine with the most real, non-degenerate content, tying
    toward higher Devanagari capture since that's this product's stated
    priority script (per PaddleOCRProvider's own docstring)."""
    candidates = []
    for name, r in results.items():
        ts = r["text_score"]
        if ts["is_degenerate_table"] or ts["char_count"] == 0:
            continue
        candidates.append((name, ts))
    if not candidates:
        return {"engine": None, "reason": "every engine produced degenerate or empty output on this page"}
    candidates.sort(key=lambda kv: (kv[1]["row_like_line_count"], kv[1]["devanagari_char_ratio"]), reverse=True)
    best_name, best_ts = candidates[0]
    return {
        "engine": best_name,
        "reason": f"{best_ts['row_like_line_count']} row-like lines, "
                  f"{best_ts['devanagari_char_ratio']:.0%} Devanagari-script characters",
    }


def run_bakeoff_on_page(page, tesseract_lang: str = "eng+hin+mar") -> Dict[str, Any]:
    """page: a pdfplumber Page. Renders the page image once, runs all
    three local engines against it, scores each, and returns a
    decision-support recommendation."""
    pil_img = page.to_image(resolution=150).original
    results = {
        "pdfplumber_native": run_pdfplumber_native(page),
        "tesseract": run_tesseract(pil_img, lang=tesseract_lang),
        "paddleocr": run_paddleocr(pil_img),
    }
    return {"page_number": page.page_number, "results": results, "recommendation": recommend(results)}
