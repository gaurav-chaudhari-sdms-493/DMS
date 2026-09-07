"""T03 regression test — the settings screen and sys_dg_config only cover
thresholds that ARE routed through config_service. Nothing stops someone
from adding a brand new hardcoded threshold constant straight into a
pipeline module, which would then be invisible from that screen and from
every tenant's ability to tune it. This scans the known threshold-sensitive
pipeline modules for module-level constants that look like thresholds
(name contains THRESHOLD/CONFIDENCE/SIMILARITY/COVERAGE, value a bare
float) and fails if one appears that isn't in the allowlist below --
forcing whoever adds a new one to either route it through sys_dg_config
(see config_service.get_float) or explain why it's a legitimate
non-configurable constant."""
import re
from pathlib import Path

import pytest

BACKEND_ROOT = Path(__file__).resolve().parent.parent

THRESHOLD_SENSITIVE_FILES = [
    "app/pipeline/vlm_extraction.py",
    "app/pipeline/table_stitch.py",
    "app/services/duplicate_service.py",
    "app/services/entity_graph_service.py",
    "app/services/search_service.py",
    "app/services/classification_service.py",
]

# name -> value, as they exist today. Adding a new entry here should come
# with a matching sys_dg_config row + config_service.get_float/get_int
# call at the constant's use site, not just an allowlist bump -- this list
# is a tripwire, not a place to launder new hardcoded values through.
KNOWN_THRESHOLD_CONSTANTS = {
    # vlm_extraction.py — ADJUDICATION_CONFIDENCE_THRESHOLD is only the
    # fallback default for get_float("table_stitch_adjudication_confidence_threshold", ...).
    "ADJUDICATION_CONFIDENCE_THRESHOLD": "0.6",
    # ROW_COVERAGE_REVIEW_THRESHOLD (T22 quality gate) is used directly,
    # never sourced from sys_dg_config -- a pre-existing gap, not this
    # test's job to fix, but it must not grow silently either.
    "ROW_COVERAGE_REVIEW_THRESHOLD": "0.4",
    # duplicate_service.py — fallback default for get_float("duplicate_fuzzy_similarity_threshold", ...).
    "DEFAULT_FUZZY_SIMILARITY_THRESHOLD": "0.92",
    # table_stitch.py — fallback defaults for the two table_stitch_* keys.
    "VERTICAL_FIELD_SET_SIMILARITY_THRESHOLD": "0.7",
    "HORIZONTAL_MIN_COMBINED_COVERAGE": "0.5",
}

THRESHOLD_CONST_RE = re.compile(
    r"^([A-Z][A-Z0-9_]*(?:THRESHOLD|CONFIDENCE|SIMILARITY|COVERAGE)[A-Z0-9_]*)\s*=\s*([\d.]+)\s*$"
)


def _find_threshold_constants(path: Path):
    found = {}
    for line in path.read_text().splitlines():
        m = THRESHOLD_CONST_RE.match(line.strip())
        if m:
            found[m.group(1)] = m.group(2)
    return found


@pytest.mark.parametrize("relpath", THRESHOLD_SENSITIVE_FILES)
def test_no_new_hardcoded_threshold_constants(relpath):
    path = BACKEND_ROOT / relpath
    if not path.exists():
        pytest.skip(f"{relpath} no longer exists")
    found = _find_threshold_constants(path)
    for name, value in found.items():
        assert name in KNOWN_THRESHOLD_CONSTANTS, (
            f"{relpath} defines a new hardcoded threshold-looking constant "
            f"{name} = {value} that isn't in this test's allowlist. If it's "
            f"meant to be tunable, add a sys_dg_config row (migration) and "
            f"read it via config_service.get_float/get_int -- it will then "
            f"show up on the admin settings screen automatically. If it's "
            f"genuinely a fixed, non-configurable constant, add it to "
            f"KNOWN_THRESHOLD_CONSTANTS in this test with a one-line reason."
        )
        assert KNOWN_THRESHOLD_CONSTANTS[name] == value, (
            f"{relpath}:{name} changed from {KNOWN_THRESHOLD_CONSTANTS[name]} "
            f"to {value} -- update KNOWN_THRESHOLD_CONSTANTS here if that "
            f"change was intentional."
        )
