"""Bounding box coordinate standardization utility (Section 0/2, decision T06).

Coordinates in VeritasDocs must always be normalized to [x0, y0, x1, y1] float fractions between 0.0 and 1.0 relative to page width and height.
Origin (0.0, 0.0) is the page's top-left corner; x grows right, y grows down.
"""

from typing import List, Optional, Tuple, Union


def normalize_bbox(
    bbox: Union[dict, List[Union[float, int]], Tuple[Union[float, int], ...]],
    page_width: Optional[float] = None,
    page_height: Optional[float] = None,
) -> Optional[List[float]]:
    """Standardize a bounding box into [x0, y0, x1, y1] normalized float format [0.0, 1.0].

    Handles:
    - Dict format {"x0": ..., "y0": ..., "x1": ..., "y1": ...} or {"left": ..., "top": ..., "right": ..., "bottom": ...}
    - 0-1000 scale integer coordinates (VLM output)
    - Raw pixel/point coordinates (given page_width, page_height)
    - Out-of-bounds values by clamping to [0.0, 1.0]
    """
    if not bbox:
        return None

    if isinstance(bbox, dict):
        if "x0" in bbox and "y0" in bbox and "x1" in bbox and "y1" in bbox:
            raw = [bbox["x0"], bbox["y0"], bbox["x1"], bbox["y1"]]
        elif "left" in bbox and "top" in bbox and "right" in bbox and "bottom" in bbox:
            raw = [bbox["left"], bbox["top"], bbox["right"], bbox["bottom"]]
        elif "x" in bbox and "y" in bbox and "width" in bbox and "height" in bbox:
            raw = [bbox["x"], bbox["y"], bbox["x"] + bbox["width"], bbox["y"] + bbox["height"]]
        else:
            return None
    elif isinstance(bbox, (list, tuple)):
        if len(bbox) != 4:
            return None
        raw = list(bbox)
    else:
        return None

    try:
        x0, y0, x1, y1 = float(raw[0]), float(raw[1]), float(raw[2]), float(raw[3])
    except (ValueError, TypeError):
        return None

    max_val = max(abs(x0), abs(y0), abs(x1), abs(y1))

    if max_val > 10.0:
        if page_width and page_height and page_width > 0 and page_height > 0:
            if max_val <= max(page_width, page_height) * 1.5:
                x0 /= page_width
                x1 /= page_width
                y0 /= page_height
                y1 /= page_height
            else:
                x0 /= 1000.0
                y0 /= 1000.0
                x1 /= 1000.0
                y1 /= 1000.0
        else:
            x0 /= 1000.0
            y0 /= 1000.0
            x1 /= 1000.0
            y1 /= 1000.0

    min_x, max_x = min(x0, x1), max(x0, x1)
    min_y, max_y = min(y0, y1), max(y0, y1)

    norm_x0 = max(0.0, min(1.0, min_x))
    norm_y0 = max(0.0, min(1.0, min_y))
    norm_x1 = max(0.0, min(1.0, max_x))
    norm_y1 = max(0.0, min(1.0, max_y))

    return [round(norm_x0, 6), round(norm_y0, 6), round(norm_x1, 6), round(norm_y1, 6)]
