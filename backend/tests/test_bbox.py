import pytest
from app.utils.bbox import normalize_bbox


def test_normalize_bbox_float_already_normalized():
    bbox = [0.1, 0.2, 0.3, 0.4]
    result = normalize_bbox(bbox)
    assert result == [0.1, 0.2, 0.3, 0.4]


def test_normalize_bbox_1000_scale_integers():
    bbox = [150, 250, 450, 850]
    result = normalize_bbox(bbox)
    assert result == [0.15, 0.25, 0.45, 0.85]


def test_normalize_bbox_pixel_dimensions():
    bbox = [100, 200, 300, 400]
    result = normalize_bbox(bbox, page_width=1000.0, page_height=2000.0)
    assert result == [0.1, 0.1, 0.3, 0.2]


def test_normalize_bbox_dict_formats():
    dict1 = {"x0": 0.1, "y0": 0.2, "x1": 0.3, "y1": 0.4}
    assert normalize_bbox(dict1) == [0.1, 0.2, 0.3, 0.4]

    dict2 = {"left": 100, "top": 200, "right": 300, "bottom": 400}
    assert normalize_bbox(dict2, page_width=1000.0, page_height=2000.0) == [0.1, 0.1, 0.3, 0.2]

    dict3 = {"x": 0.1, "y": 0.2, "width": 0.2, "height": 0.3}
    assert normalize_bbox(dict3) == [0.1, 0.2, 0.3, 0.5]


def test_normalize_bbox_out_of_bounds_clamping():
    bbox = [-0.1, -0.05, 1.2, 1.5]
    result = normalize_bbox(bbox)
    assert result == [0.0, 0.0, 1.0, 1.0]


def test_normalize_bbox_invalid():
    assert normalize_bbox(None) is None
    assert normalize_bbox([]) is None
    assert normalize_bbox([1, 2, 3]) is None
    assert normalize_bbox("invalid") is None
