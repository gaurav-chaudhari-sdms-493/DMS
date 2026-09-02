"""T98 — coverage-ratchet check.

pytest.ini's --cov-fail-under is a floor: it already fails CI the moment
coverage drops below it. What was missing is the other half — nothing
ever nudged that floor UP as real coverage grew, so it could sit stale
at its original number indefinitely even while the suite genuinely
improved. This script closes that gap without auto-committing back to
the repo (safer than a bot commit: no write-permission requirements, no
merge-conflict risk, no surprise history) — it just fails CI with an
actionable message once actual coverage has drifted meaningfully above
the floor, so a human bumps pytest.ini in the same PR that earned the
improvement.

Run after `pytest --cov-report=json` has produced backend/coverage.json.
"""
import json
import re
import sys
from pathlib import Path

TOLERANCE_POINTS = 3.0  # slack so this doesn't fail on every 1% fluctuation


def main() -> int:
    backend_dir = Path(__file__).resolve().parent.parent
    coverage_json = backend_dir / "coverage.json"
    pytest_ini = backend_dir / "pytest.ini"

    if not coverage_json.exists():
        print(f"::warning::{coverage_json} not found — run pytest with --cov-report=json first. Skipping ratchet check.")
        return 0

    data = json.loads(coverage_json.read_text())
    actual_pct = data["totals"]["percent_covered"]

    ini_text = pytest_ini.read_text()
    match = re.search(r"--cov-fail-under=(\d+)", ini_text)
    if not match:
        print("::warning::No --cov-fail-under found in pytest.ini — skipping ratchet check.")
        return 0
    floor_pct = int(match.group(1))

    print(f"Actual coverage: {actual_pct:.1f}% | pytest.ini floor: {floor_pct}%")

    if actual_pct >= floor_pct + TOLERANCE_POINTS:
        new_floor = int(actual_pct)  # round down — stay a real floor, not a ceiling that immediately fails
        print(
            f"::error::Coverage ({actual_pct:.1f}%) has drifted {actual_pct - floor_pct:.1f} points above "
            f"the pytest.ini floor ({floor_pct}%). Raise --cov-fail-under to {new_floor} in backend/pytest.ini "
            f"in this PR so the floor tracks real progress (T98)."
        )
        return 1

    print("Coverage floor is up to date.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
