import pytest

from app.pipeline.handlers.spread_join import join_spread
from app.pipeline.handlers.ditto_chain import expand_ditto_chains
from app.pipeline.handlers.continuation_merge import merge_continuation_rows
from app.pipeline.handlers.blob_cell_parser import parse_blob_cell


# --- Handler 1: multi-page spread join ---------------------------------

def test_spread_join_merges_matching_serials():
    left = [
        {"no": 12, "khatedar": "Ramrao Patil", "area": "1 ha 25 are"},
        {"no": 13, "khatedar": "Sitabai Deshmukh", "area": "0 ha 80 are"},
    ]
    right = [
        {"no": 12, "shera": "", "value": "Rs. 1,240"},
        {"no": 13, "shera": "disputed", "value": "Rs. 900"},
    ]
    result = join_spread(left, right)
    assert result.status == "ok"
    assert len(result.rows) == 2
    row_12 = next(r for r in result.rows if r["no"] == 12)
    assert row_12["khatedar"] == "Ramrao Patil"
    assert row_12["value"] == "Rs. 1,240"


def test_spread_join_sends_mismatched_halves_to_review():
    left = [{"no": 12, "khatedar": "Ramrao Patil"}, {"no": 13, "khatedar": "Sitabai Deshmukh"}]
    right = [{"no": 12, "value": "Rs. 1,240"}]  # missing row 13 — a wrong join would misattribute land
    result = join_spread(left, right)
    assert result.status == "needs_review"
    assert "13" in result.reason


# --- Handler 2: ditto-chain expansion -----------------------------------

def test_ditto_chain_expands_per_column_independently():
    """Section 4's own worked example: row 23 keeps khatedar but starts a
    new village; row 24 then copies that new village."""
    rows = [
        {"no": 21, "khatedar": "Ramrao Patil", "village": "Basmath"},
        {"no": 22, "khatedar": ",,", "village": ",,"},
        {"no": 23, "khatedar": ",,", "village": "Kalamnuri"},
        {"no": 24, "khatedar": "Sitabai Deshmukh", "village": ",,"},
    ]
    out = expand_ditto_chains(rows, columns=["khatedar", "village"])

    assert out[0]["khatedar"] == "Ramrao Patil" and out[0]["_inherited_columns"] == []
    assert out[1]["khatedar"] == "Ramrao Patil" and "khatedar" in out[1]["_inherited_columns"]
    assert out[1]["village"] == "Basmath" and "village" in out[1]["_inherited_columns"]
    assert out[2]["khatedar"] == "Ramrao Patil" and "khatedar" in out[2]["_inherited_columns"]
    assert out[2]["village"] == "Kalamnuri" and "village" not in out[2]["_inherited_columns"]
    assert out[3]["khatedar"] == "Sitabai Deshmukh" and "khatedar" not in out[3]["_inherited_columns"]
    assert out[3]["village"] == "Kalamnuri" and "village" in out[3]["_inherited_columns"]


def test_ditto_chain_flags_unresolved_instead_of_raising():
    """TS5 — a broken source chain (nothing above to copy) is flagged
    per-cell for human review rather than raising and losing the whole
    segment's ditto resolution over one broken cell."""
    rows = [{"no": 1, "khatedar": ",,"}]
    out = expand_ditto_chains(rows, columns=["khatedar"])
    assert out[0]["_unresolved_ditto_columns"] == ["khatedar"]
    assert out[0]["_ditto_verbatim"] == {"khatedar": ",,"}
    assert "khatedar" not in out[0]["_inherited_columns"]


def test_ditto_chain_matches_real_register_convention():
    """TS5 — real bug found against an actual 1973 Maharashtra Waqf Board
    gazette table, which writes "Do." (capitalized, trailing period), not
    the bare lowercase "do" this only originally matched."""
    rows = [
        {"no": 180, "shia_or_sunni": "Sunni", "object": "Religious"},
        {"no": 181, "shia_or_sunni": "Do.", "object": "Do."},
        {"no": 182, "shia_or_sunni": "DO", "object": "do."},
    ]
    out = expand_ditto_chains(rows, columns=["shia_or_sunni", "object"])
    assert out[1]["shia_or_sunni"] == "Sunni"
    assert out[1]["object"] == "Religious"
    assert out[2]["shia_or_sunni"] == "Sunni"
    assert out[2]["object"] == "Religious"


def test_ditto_chain_stores_verbatim_alongside_resolved_value():
    rows = [
        {"no": 1, "khatedar": "Ramrao Patil"},
        {"no": 2, "khatedar": "Do."},
    ]
    out = expand_ditto_chains(rows, columns=["khatedar"])
    assert out[1]["khatedar"] == "Ramrao Patil"  # resolved
    assert out[1]["_ditto_verbatim"]["khatedar"] == "Do."  # literal reading preserved
    assert "khatedar" in out[1]["_inherited_columns"]  # was_ditto_filled


def test_ditto_chain_anchor_resets_all_columns_on_genuine_change():
    """Opt-in chain_anchor_column: a genuine (non-ditto) change resets
    EVERY column's chain, not just its own."""
    rows = [
        {"no": 1, "khatedar": "Ramrao Patil", "village": "Basmath"},
        {"no": 2, "khatedar": ",,", "village": "Kalamnuri"},  # village genuinely changes
        {"no": 3, "khatedar": ",,", "village": ",,"},  # khatedar ditto now has nothing to copy
    ]
    out = expand_ditto_chains(rows, columns=["khatedar", "village"], chain_anchor_column="village")
    assert out[1]["village"] == "Kalamnuri"
    assert "khatedar" in out[1]["_unresolved_ditto_columns"]  # reset by the anchor change
    assert out[2]["village"] == "Kalamnuri"  # village itself still chains fine
    assert "khatedar" in out[2]["_unresolved_ditto_columns"]  # still broken -- nothing valid since the reset


def test_ditto_chain_without_anchor_lets_unrelated_columns_persist_across_change():
    """Regression guard: without an explicit chain_anchor_column, a
    village change must NOT reset other columns (see
    test_ditto_chain_expands_per_column_independently — this is the
    real, already-validated behavior an anchor-based rule must not
    silently override for callers who never opted in)."""
    rows = [
        {"no": 1, "khatedar": "Ramrao Patil", "village": "Basmath"},
        {"no": 2, "khatedar": ",,", "village": "Kalamnuri"},
    ]
    out = expand_ditto_chains(rows, columns=["khatedar", "village"])
    assert out[1]["khatedar"] == "Ramrao Patil"
    assert "khatedar" in out[1]["_inherited_columns"]


# --- Handler 3: continuation-row merge -----------------------------------

def test_continuation_merge_joins_blank_serial_into_previous_record():
    """Section 4's own worked example: kabrastan entry split across pages 4/5."""
    rows = [
        {"no": 47, "description": "kabrastan, survey no. 47, north — road, south — well, east —"},
        {"no": None, "description": "school, west — road"},
    ]
    out = merge_continuation_rows(rows)

    assert len(out) == 1
    assert out[0]["no"] == 47
    assert out[0]["description"] == (
        "kabrastan, survey no. 47, north — road, south — well, east — school, west — road"
    )
    assert out[0]["_source_row_indices"] == [0, 1]


def test_continuation_merge_raises_when_first_row_has_blank_serial():
    rows = [{"no": None, "description": "orphaned continuation"}]
    with pytest.raises(ValueError):
        merge_continuation_rows(rows)


# --- Handler 4: blob-cell parse -------------------------------------------

def test_blob_cell_parses_washim_register_example():
    """Section 4's own worked example, exact expected numbers included."""
    text = (
        "मौजे वाशिम — S.No. 121/2A & 121/2B, area 1 हे 25 आर, "
        "construction 4500 sqft, open space 300 चौ.मी., CTS 88, Akker 2.5"
    )
    result = parse_blob_cell(text)

    assert result.survey_numbers == ["121/2A", "121/2B"]
    assert result.cts == "88"
    assert result.area_sqm == 12500.0
    assert result.built_sqm == 418.06
    assert result.open_space_sqm == 300.0
    assert any("Akker" in f for f in result.flags)


def test_blob_cell_handles_missing_fields_gracefully():
    result = parse_blob_cell("S.No. 45, area 2 आर")
    assert result.survey_numbers == ["45"]
    assert result.area_sqm == 200.0
    assert result.built_sqm is None
    assert result.open_space_sqm is None
    assert result.flags == []
