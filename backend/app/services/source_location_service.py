"""T05 — locate a non-VLM metadata value on the page it actually came from.

extractor.py already computes a word-level bbox for every word pdfplumber
found on each page (normalised 0-1, top-left origin, per T06's coordinate
contract) and chunker.py carries it through per page instead of discarding
it. This module is the missing last step: given the LLM-extracted value
string and the document's per-page text/word list, find the tightest
contiguous run of words whose text matches the value, and return its
page number + unioned bounding box.

Deliberately conservative: this only returns a region on an exact
(whitespace/case-normalised) match. The LLM that produced the value is
free to paraphrase or reformat it (e.g. "15 March 2024" for a page that
prints "15/03/2024"), and when it does, there is no reliable region to
point at -- returning None is the honest result, not a guessed box.
"""
import re
from typing import Any, Dict, List, Optional

# A value shorter than this is too likely to false-positive-match
# unrelated boilerplate text on the page (e.g. a single digit, "OK").
_MIN_MATCH_LENGTH = 2

# Values are short (a name, a date, a doc type) -- no real value should
# need more words than this to match; caps the cost of growing a window
# across a whole page's word list at every start position.
_MAX_WINDOW_WORDS = 20


def _normalize(s: str) -> str:
    return re.sub(r"\s+", " ", (s or "")).strip().lower()


def _locate_in_words(needle: str, words: List[Dict[str, Any]]) -> Optional[Dict[str, float]]:
    n = len(words)
    for start in range(n):
        joined = ""
        x0 = y0 = 1.0
        x1 = y1 = 0.0
        for end in range(start, min(start + _MAX_WINDOW_WORDS, n)):
            w = words[end]
            word_text = w.get("text", "")
            joined = f"{joined} {word_text}".strip() if joined else word_text
            try:
                x0, y0 = min(x0, w["x0"]), min(y0, w["y0"])
                x1, y1 = max(x1, w["x1"]), max(y1, w["y1"])
            except KeyError:
                break
            norm_joined = _normalize(joined)
            if norm_joined == needle:
                return {"x0": x0, "y0": y0, "x1": x1, "y1": y1}
            if len(norm_joined) > len(needle) + 5:
                break
    return None


def locate_value_in_pages(value_text: Any, pages: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    """Find the page + bbox a metadata value's text most likely came from.

    `pages` is the same per-page structure extractor.py/chunker.py produce:
    each entry has "page_number", "text", and "words" (a list of
    {"text", "x0", "y0", "x1", "y1"} dicts, already normalised 0-1).

    Returns {"page_number", "x0", "y0", "x1", "y1"} on the first page the
    value can be exactly located on, or None if it can't be located on
    any page (not an error -- most non-string values, and any paraphrased
    string value, legitimately have no locatable region).
    """
    if not isinstance(value_text, str):
        return None
    needle = _normalize(value_text)
    if len(needle) < _MIN_MATCH_LENGTH:
        return None

    for page in pages:
        haystack = _normalize(page.get("text", ""))
        if needle not in haystack:
            continue
        words = page.get("words") or []
        if not words:
            continue
        region = _locate_in_words(needle, words)
        if region:
            return {"page_number": page.get("page_number", 1), **region}
    return None
