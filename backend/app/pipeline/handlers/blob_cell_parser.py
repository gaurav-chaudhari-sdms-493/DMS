import re
from dataclasses import dataclass, field
from typing import List, Optional

# Unit conversions to square metres. "Akker" is deliberately excluded —
# it means different things in different districts, so it's flagged for
# a person instead of silently guessing a number (Section 4, Handler 4).
SQM_PER_HECTARE = 10000.0
SQM_PER_ARE = 100.0
SQM_PER_GUNTHA = 101.0  # per Section 0 glossary: "1 guntha ≈ 101 sq m"
SQM_PER_SQFT = 0.092903

# Devanagari vowel-sign characters (matras) are Unicode combining marks, not
# \w — a trailing \b after them never fires, so these use a lookahead on the
# next separator instead.
_END = r"(?=\s|,|\.|$)"
HECTARE_RE = re.compile(rf"(\d+(?:\.\d+)?)\s*(?:हे{_END}|ha\b|hectare)", re.IGNORECASE)
ARE_RE = re.compile(rf"(\d+(?:\.\d+)?)\s*(?:आर{_END}|are\b)", re.IGNORECASE)
GUNTHA_RE = re.compile(r"(\d+(?:\.\d+)?)\s*(?:guntha)", re.IGNORECASE)
SQFT_RE = re.compile(rf"(\d+(?:\.\d+)?)\s*(?:sq\.?\s*ft\.?|sqft|चौ\.?\s*फूट{_END})", re.IGNORECASE)
SQM_RE = re.compile(rf"(\d+(?:\.\d+)?)\s*(?:sq\.?\s*m\.?|sqm|चौ\.?\s*मी\.?{_END})", re.IGNORECASE)
CTS_RE = re.compile(r"CTS\s*(?:no\.?)?\s*(\d+)", re.IGNORECASE)
SURVEY_RE = re.compile(r"(?:S\.?No\.?|survey\s*no\.?)\s*([0-9]+(?:/[0-9A-Za-z]+)?(?:\s*&\s*[0-9]+(?:/[0-9A-Za-z]+)?)*)", re.IGNORECASE)
AKKER_RE = re.compile(r"Akker\s*(\d+(?:\.\d+)?)", re.IGNORECASE)


@dataclass
class BlobCellParse:
    survey_numbers: List[str] = field(default_factory=list)
    cts: Optional[str] = None
    area_sqm: Optional[float] = None
    built_sqm: Optional[float] = None
    open_space_sqm: Optional[float] = None
    flags: List[str] = field(default_factory=list)
    raw_text: str = ""


def _sum_area_terms(text: str) -> Optional[float]:
    """Sum every hectare/are/guntha term found in one contiguous area phrase."""
    total = 0.0
    found = False
    for regex, factor in ((HECTARE_RE, SQM_PER_HECTARE), (ARE_RE, SQM_PER_ARE), (GUNTHA_RE, SQM_PER_GUNTHA)):
        m = regex.search(text)
        if m:
            total += float(m.group(1)) * factor
            found = True
    return total if found else None


def parse_blob_cell(text: str) -> BlobCellParse:
    """Handler 4 — parse one free-text cell mixing Marathi/English (Section 4).

    Normalises every area figure into square metres while keeping the
    original text available for review. "Akker" is never silently
    converted — it's flagged, since its meaning varies by district.
    """
    result = BlobCellParse(raw_text=text)

    survey_match = SURVEY_RE.search(text)
    if survey_match:
        result.survey_numbers = [s.strip() for s in survey_match.group(1).split("&")]

    cts_match = CTS_RE.search(text)
    if cts_match:
        result.cts = cts_match.group(1)

    # Area (hectare/are/guntha combination) — look for the phrase following "area"
    area_phrase_match = re.search(r"area\s+([^,]+)", text, re.IGNORECASE)
    if area_phrase_match:
        result.area_sqm = _sum_area_terms(area_phrase_match.group(1))

    # Built-up / construction area (sqft)
    built_phrase_match = re.search(r"construction\s+([^,]+)", text, re.IGNORECASE)
    if built_phrase_match:
        sqft_match = SQFT_RE.search(built_phrase_match.group(1))
        if sqft_match:
            result.built_sqm = round(float(sqft_match.group(1)) * SQM_PER_SQFT, 2)

    # Open space (already in sqm in these registers)
    open_phrase_match = re.search(r"open space\s+([^,]+)", text, re.IGNORECASE)
    if open_phrase_match:
        sqm_match = SQM_RE.search(open_phrase_match.group(1))
        if sqm_match:
            result.open_space_sqm = float(sqm_match.group(1))

    akker_match = AKKER_RE.search(text)
    if akker_match:
        result.flags.append(f"Akker {akker_match.group(1)} — district-dependent unit, needs human review")

    return result
