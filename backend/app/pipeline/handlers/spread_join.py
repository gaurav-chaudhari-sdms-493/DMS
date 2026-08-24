from dataclasses import dataclass, field
from typing import Any, Dict, List

SERIAL_COLUMN = "no"


@dataclass
class SpreadJoinResult:
    status: str  # "ok" | "needs_review"
    rows: List[Dict[str, Any]] = field(default_factory=list)
    reason: str = ""


def join_spread(left_rows: List[Dict[str, Any]], right_rows: List[Dict[str, Any]]) -> SpreadJoinResult:
    """Handler 1 — join a two-page spread by serial number (Section 4).

    A register entry runs across two facing pages: the left half has one
    set of columns, the right half has the rest, and the two are matched
    by serial number. If the halves disagree on which serials they carry,
    do not guess a join — a wrong join puts one family's valuation on
    another family's land. Send it to a person instead.
    """
    left_by_serial = {row[SERIAL_COLUMN]: row for row in left_rows}
    right_by_serial = {row[SERIAL_COLUMN]: row for row in right_rows}

    if set(left_by_serial.keys()) != set(right_by_serial.keys()):
        only_left = set(left_by_serial.keys()) - set(right_by_serial.keys())
        only_right = set(right_by_serial.keys()) - set(left_by_serial.keys())
        return SpreadJoinResult(
            status="needs_review",
            reason=(
                f"left/right page halves disagree on serial numbers "
                f"(only on left: {sorted(only_left)}, only on right: {sorted(only_right)})"
            ),
        )

    merged = []
    for serial in sorted(left_by_serial.keys()):
        row = {**left_by_serial[serial], **right_by_serial[serial]}
        merged.append(row)

    return SpreadJoinResult(status="ok", rows=merged)
