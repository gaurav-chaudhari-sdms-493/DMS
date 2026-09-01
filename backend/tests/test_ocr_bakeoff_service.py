from app.services.ocr_bakeoff_service import score_text, score_bbox_units, recommend


def test_score_text_counts_row_like_lines_with_digits():
    text = "197  Do.  Chilla Madar Saheb  100.00\nsome narrative sentence with no numbers\n201  New Entry  55.50"
    s = score_text(text, "test")
    assert s["row_like_line_count"] == 2
    assert s["line_count"] == 3
    assert s["char_count"] == len(text)


def test_score_text_devanagari_ratio():
    text = "वक्फ मंडळ Aurangabad"
    s = score_text(text, "test")
    assert s["devanagari_char_ratio"] > 0.0
    assert s["devanagari_char_ratio"] < 1.0


def test_score_text_empty_string_has_zero_ratio_no_crash():
    s = score_text("", "test")
    assert s["char_count"] == 0
    assert s["devanagari_char_ratio"] == 0.0
    assert s["is_degenerate_table"] is False


def _degenerate_row(serial: int, placeholder_columns: int = 10) -> str:
    """One real serial-number cell + N placeholder-only cells, mirroring
    the real gazette's own sparse-row convention (TS1's build note:
    "cells were mostly '..' placeholders")."""
    return "  ".join([str(serial)] + [".."] * placeholder_columns)


def test_score_text_flags_degenerate_table_over_90pct_empty():
    text = "\n".join(_degenerate_row(i) for i in range(10))
    s = score_text(text, "test")
    assert s["is_degenerate_table"] is True
    assert s["empty_pseudo_cell_ratio"] > 0.90


def test_score_text_does_not_flag_real_dense_table():
    lines = [f"{i}  Survey No {i*3}  Valuation {i*100}.00" for i in range(1, 11)]
    text = "\n".join(lines)
    s = score_text(text, "test")
    assert s["is_degenerate_table"] is False
    assert s["row_like_line_count"] == 10


def test_score_bbox_units_computes_coverage_by_granularity():
    units = [{"text": "a", "bbox": {"x0": 0}}, {"text": "b", "bbox": None}, {"text": "c", "bbox": {"x0": 1}}]
    s = score_bbox_units(units, "tesseract", "word")
    assert s["unit_count"] == 3
    assert s["units_with_bbox"] == 2
    assert abs(s["bbox_coverage"] - (2 / 3)) < 1e-3
    assert s["granularity"] == "word"


def test_score_bbox_units_empty_list_no_crash():
    s = score_bbox_units([], "paddleocr", "line")
    assert s["unit_count"] == 0
    assert s["bbox_coverage"] == 0.0


def test_recommend_picks_engine_with_more_rows_and_skips_degenerate():
    good_text = "\n".join(f"{i}  Survey No {i}  Val {i*10}.00" for i in range(1, 6))
    # More "row-like" lines than good_text, but >90% placeholder cells —
    # must still lose to the non-degenerate engine.
    degenerate_text = "\n".join(_degenerate_row(i) for i in range(1, 21))
    results = {
        "engine_a": {"text_score": score_text(good_text, "engine_a")},
        "engine_b": {"text_score": score_text(degenerate_text, "engine_b")},
    }
    assert results["engine_b"]["text_score"]["row_like_line_count"] > results["engine_a"]["text_score"]["row_like_line_count"]
    rec = recommend(results)
    assert rec["engine"] == "engine_a"


def test_recommend_returns_none_when_every_engine_degenerate_or_empty():
    results = {
        "engine_a": {"text_score": score_text("", "engine_a")},
        "engine_b": {"text_score": score_text("\n".join(_degenerate_row(i) for i in range(1, 11)), "engine_b")},
    }
    rec = recommend(results)
    assert rec["engine"] is None


def test_recommend_ties_toward_higher_devanagari_ratio():
    text_en = "\n".join(f"{i}  Survey {i}  Val {i}.00" for i in range(1, 6))
    text_dv = "\n".join(f"{i}  वक्फ {i}  Val {i}.00" for i in range(1, 6))
    results = {
        "engine_en": {"text_score": score_text(text_en, "engine_en")},
        "engine_dv": {"text_score": score_text(text_dv, "engine_dv")},
    }
    rec = recommend(results)
    assert rec["engine"] == "engine_dv"
