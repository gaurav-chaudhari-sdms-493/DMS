import pytest
from unittest.mock import AsyncMock

from app.pipeline.table_stitch import (
    field_set, jaccard, shape_hash, decide_relation,
    match_rows_by_key, pair_leftovers_by_position, join_rows_horizontally,
    adjudicate_structure,
)


def _f(value, bbox=None, confidence=0.9):
    d = {"value": value, "confidence": confidence}
    if bbox:
        d["bbox"] = bbox
    return d


def test_field_set_ignores_blank_and_missing_values():
    rows = [
        {"owner": _f("Priya"), "area": _f("")},
        {"owner": _f(""), "valuation": _f("1000")},
    ]
    assert field_set(rows) == frozenset({"owner", "valuation"})


def test_field_set_empty_for_all_blank_rows():
    rows = [{"owner": _f(""), "area": _f(None)}]
    assert field_set(rows) == frozenset()


def test_jaccard_identical_and_disjoint():
    assert jaccard(frozenset({"a", "b"}), frozenset({"a", "b"})) == 1.0
    assert jaccard(frozenset({"a"}), frozenset({"b"})) == 0.0
    assert jaccard(frozenset(), frozenset()) == 1.0


def test_shape_hash_stable_and_order_independent():
    h1 = shape_hash(frozenset({"owner", "area"}), frozenset({"valuation"}))
    h2 = shape_hash(frozenset({"area", "owner"}), frozenset({"valuation"}))
    assert h1 == h2
    h3 = shape_hash(frozenset({"owner"}), frozenset({"valuation"}))
    assert h1 != h3


def test_decide_relation_vertical_on_high_similarity():
    fields_a = frozenset({"owner", "area", "village"})
    fields_b = frozenset({"owner", "area", "village"})
    result = decide_relation(fields_a, fields_b, fields_a)
    assert result.relation == "vertical"
    assert result.certain is True


def test_decide_relation_vertical_on_headerless_continuation():
    fields_a = frozenset({"owner", "area"})
    result = decide_relation(fields_a, frozenset(), fields_a)
    assert result.relation == "vertical"
    assert result.certain is True


def test_decide_relation_horizontal_on_disjoint_full_coverage():
    full = frozenset({"serial", "owner", "area", "valuation", "remarks"})
    fields_a = frozenset({"serial", "owner", "area"})
    fields_b = frozenset({"valuation", "remarks"})
    result = decide_relation(fields_a, fields_b, full)
    assert result.relation == "horizontal"
    assert result.certain is True


def test_decide_relation_ambiguous_on_partial_overlap():
    full = frozenset({"serial", "owner", "area", "valuation", "remarks", "notes", "date"})
    fields_a = frozenset({"serial", "owner"})
    fields_b = frozenset({"owner", "valuation"})
    result = decide_relation(fields_a, fields_b, full)
    assert result.relation == "ambiguous"
    assert result.certain is False


def test_match_rows_by_key_separates_matched_and_leftovers():
    left = [{"no": _f("1"), "owner": _f("A")}, {"no": _f("2"), "owner": _f("B")}]
    right = [{"no": _f("1"), "valuation": _f("100")}, {"no": _f("3"), "valuation": _f("300")}]
    matched, left_only, right_only = match_rows_by_key(left, right, "no")
    assert len(matched) == 1
    assert matched[0][0]["owner"]["value"] == "A"
    assert len(left_only) == 1 and left_only[0]["owner"]["value"] == "B"
    assert len(right_only) == 1 and right_only[0]["valuation"]["value"] == "300"


def test_pair_leftovers_1to1_by_vertical_position():
    left_only = [{"desc": _f("second property", bbox=[0.1, 0.5, 0.9, 0.6])}]
    right_only = [{"valuation": _f("200", bbox=[0.1, 0.5, 0.5, 0.6])}]
    groups = pair_leftovers_by_position(left_only, right_only)
    assert groups == {0: [0]}


def test_pair_leftovers_n_to_1_containment():
    # one left row spans two right rows (one waqf entry, two properties)
    left_only = [{"desc": _f("combined entry", bbox=[0.1, 0.4, 0.9, 0.7])}]
    right_only = [
        {"valuation": _f("100", bbox=[0.1, 0.40, 0.5, 0.50])},
        {"valuation": _f("150", bbox=[0.1, 0.55, 0.5, 0.65])},
    ]
    groups = pair_leftovers_by_position(left_only, right_only)
    assert groups == {0: [0, 1]}


def test_pair_leftovers_returns_none_without_bbox_data():
    left_only = [{"desc": {"value": "x"}}]  # no bbox
    right_only = [{"valuation": {"value": "y"}}]
    assert pair_leftovers_by_position(left_only, right_only) is None


def test_pair_leftovers_returns_none_when_center_falls_outside_any_span():
    left_only = [{"desc": _f("a", bbox=[0.1, 0.1, 0.9, 0.2])}]
    right_only = [{"valuation": _f("y", bbox=[0.1, 0.8, 0.9, 0.9])}]  # far away, no containment
    assert pair_leftovers_by_position(left_only, right_only) is None


def test_join_rows_horizontally_exact_match_same_as_join_spread():
    left = [{"no": _f("1"), "owner": _f("Priya")}]
    right = [{"no": _f("1"), "valuation": _f("1000")}]
    result = join_rows_horizontally(left, right, "no")
    assert result.status == "ok"
    assert len(result.pairs) == 1


def test_join_rows_horizontally_needs_review_on_total_disagreement():
    """Regression guard: this exact scenario is what
    test_spread_extraction_writes_join_mismatch_fact_on_serial_disagreement
    exercises end-to-end — zero shared keys must never be silently
    positionally paired, only a genuine partial-overlap leftover should be."""
    left = [{"no": _f("1"), "owner": _f("Priya")}]
    right = [{"no": _f("2"), "valuation": _f("1000")}]
    result = join_rows_horizontally(left, right, "no")
    assert result.status == "needs_review"
    assert "no shared" in result.reason


def test_join_rows_horizontally_reconciles_uneven_leftover_by_position():
    left = [
        {"no": _f("1"), "owner": _f("Priya", bbox=[0.1, 0.1, 0.5, 0.2])},
        {"no": _f("2"), "owner": _f("Combined Entry", bbox=[0.1, 0.3, 0.5, 0.5])},
    ]
    right = [
        {"no": _f("1"), "valuation": _f("100", bbox=[0.5, 0.1, 0.9, 0.2])},
        {"valuation": _f("200", bbox=[0.5, 0.30, 0.9, 0.38])},  # no "no" — extra property row
        {"valuation": _f("250", bbox=[0.5, 0.40, 0.9, 0.48])},  # no "no" — extra property row
    ]
    result = join_rows_horizontally(left, right, "no")
    assert result.status == "ok"
    assert len(result.pairs) == 3  # 1 exact match + 2 positionally-paired leftovers


@pytest.mark.asyncio
async def test_adjudicate_structure_parses_valid_response():
    fake_llm = AsyncMock()
    fake_llm.complete.return_value = '{"relation": "vertical", "confidence": 0.85, "reason": "same columns"}'
    verdict = await adjudicate_structure(fake_llm, frozenset({"owner"}), frozenset({"owner"}), frozenset({"owner", "area"}))
    assert verdict.relation == "vertical"
    assert verdict.confidence == 0.85


@pytest.mark.asyncio
async def test_adjudicate_structure_returns_none_on_malformed_response():
    fake_llm = AsyncMock()
    fake_llm.complete.return_value = "not json at all"
    verdict = await adjudicate_structure(fake_llm, frozenset({"owner"}), frozenset({"area"}), frozenset({"owner", "area"}))
    assert verdict is None


@pytest.mark.asyncio
async def test_adjudicate_structure_returns_none_when_llm_raises():
    fake_llm = AsyncMock()
    fake_llm.complete.side_effect = RuntimeError("no local LLM provider")
    verdict = await adjudicate_structure(fake_llm, frozenset({"owner"}), frozenset({"area"}), frozenset({"owner", "area"}))
    assert verdict is None
