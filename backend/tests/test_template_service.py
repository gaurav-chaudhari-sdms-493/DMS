from app.services.template_service import classify_confidence


def test_classify_confidence_no_confidence_is_in_review():
    assert classify_confidence({}, None) == "in_review"


def test_classify_confidence_above_default_threshold_is_machine():
    assert classify_confidence({}, 0.9) == "machine"


def test_classify_confidence_below_default_threshold_is_in_review():
    assert classify_confidence({}, 0.5) == "in_review"


def test_classify_confidence_respects_field_level_bands():
    field_def = {"confidence_bands": {"auto_commit": 0.95, "review_floor": 0.5}}
    assert classify_confidence(field_def, 0.9) == "in_review"  # below this field's stricter band
    assert classify_confidence(field_def, 0.97) == "machine"


def test_classify_confidence_handwritten_never_auto_commits():
    """T30 — a handwritten field never lands as 'machine', no matter how
    confident the model is."""
    assert classify_confidence({}, 0.99, is_handwritten=True) == "in_review"
    assert classify_confidence({}, None, is_handwritten=True) == "in_review"
