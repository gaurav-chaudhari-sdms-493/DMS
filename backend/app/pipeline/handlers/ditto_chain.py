from typing import Any, Dict, List

# Common ways a register marks "same as the row above" instead of repeating
# the value (Section 0: ditto mark).
DITTO_MARKS = {",,", '"', "do", "-do-", "″", "''"}


def expand_ditto_chains(rows: List[Dict[str, Any]], columns: List[str]) -> List[Dict[str, Any]]:
    """Handler 2 — expand ditto marks per column (Section 4).

    Each column has its own chain: a ditto mark copies the nearest
    non-ditto value above it *in that column*, independent of what the
    other columns are doing in the same row. Every copied value is
    labelled inherited=True so the person checking knows it was never
    actually written on the page.

    `rows` is mutated into new dicts; the input is left untouched.
    """
    last_value: Dict[str, Any] = {}
    out: List[Dict[str, Any]] = []

    for row in rows:
        new_row = dict(row)
        inherited: List[str] = []

        for col in columns:
            raw = row.get(col)
            is_ditto = isinstance(raw, str) and raw.strip() in DITTO_MARKS

            if is_ditto:
                if col not in last_value:
                    raise ValueError(f"ditto mark in column '{col}' has nothing above it to copy")
                new_row[col] = last_value[col]
                inherited.append(col)
            else:
                last_value[col] = raw

        new_row["_inherited_columns"] = inherited
        out.append(new_row)

    return out
