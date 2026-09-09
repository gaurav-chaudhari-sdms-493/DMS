def collapse_blank_lines(content: str) -> str:
    """Chandra's (and PaddleOCR's) line-based OCR reads a sparse form
    layout -- a label and its value visually a few centimeters apart --
    as one text line each, with a blank line per gap of whitespace in
    between. A wide gap (a label at the page's left edge and its value
    further right, or a tall gap above/below) can turn into 4-6 blank
    lines between them. Harmless for a human reading the raw OCR text
    (word order is unchanged), but real damage downstream: never alters
    word order or content, purely removes empty lines, so a label lands
    immediately next to its value the way it actually reads on the page.
    """
    lines = [ln.strip() for ln in content.splitlines()]
    return "\n".join(ln for ln in lines if ln)
