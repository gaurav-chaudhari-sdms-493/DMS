from typing import Any, Dict, List, Optional

SERIAL_COLUMN = "no"
MERGE_TEXT_COLUMNS_DEFAULT = ["description"]


def _is_blank(value: Optional[str]) -> bool:
    return value is None or str(value).strip() == ""


def merge_continuation_rows(
    rows: List[Dict[str, Any]],
    text_columns: List[str] = None,
) -> List[Dict[str, Any]]:
    """Handler 3 — merge a blank-serial continuation row into the record above (Section 4).

    A blank serial number in the first row of a page means the entry
    above is still running. Reading it as its own row produces a half
    record; merging it produces the complete one. The merged record
    tracks which source rows it came from, since a fact built from a
    merge spans more than one page (region is a list, per T06).

    `rows` must already be in reading order (the order they appear on
    the page(s), top to bottom, left page before right).
    """
    text_columns = text_columns or MERGE_TEXT_COLUMNS_DEFAULT
    out: List[Dict[str, Any]] = []

    for idx, row in enumerate(rows):
        serial = row.get(SERIAL_COLUMN)

        if _is_blank(serial):
            if not out:
                raise ValueError(f"row {idx} has a blank serial number but there is no prior row to merge into")
            prev = out[-1]
            for col in text_columns:
                if col in row and row[col]:
                    prev_text = (prev.get(col) or "").rstrip()
                    cont_text = str(row[col]).strip()
                    prev[col] = f"{prev_text} {cont_text}".strip()
            prev.setdefault("_source_row_indices", [idx - 1]).append(idx)
        else:
            new_row = dict(row)
            new_row["_source_row_indices"] = [idx]
            out.append(new_row)

    return out
