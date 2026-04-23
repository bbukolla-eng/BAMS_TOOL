"""
Tests for PDF geometry extraction helper functions.
The pure helpers are duplicated here to avoid importing fitz (PyMuPDF)
which is only available in the full Docker environment.
"""


def _pts_to_ft(x_pts: float, y_pts: float, page_height_pts: float, scale_px_per_ft: float):
    """Mirror of ai.pdf_extractor._pts_to_ft"""
    pts_per_inch = 72.0
    px_per_inch = 96.0
    px_per_pt = px_per_inch / pts_per_inch
    x_px = x_pts * px_per_pt
    y_px = (page_height_pts - y_pts) * px_per_pt
    if scale_px_per_ft and scale_px_per_ft > 0:
        return x_px / scale_px_per_ft, y_px / scale_px_per_ft
    return x_px, y_px


def _color_to_hex(color) -> str:
    """Mirror of ai.pdf_extractor._color_to_hex"""
    if not color:
        return "#000000"
    if isinstance(color, (list, tuple)) and len(color) == 3:
        r, g, b = [int(c * 255) for c in color]
        return f"#{r:02x}{g:02x}{b:02x}"
    return "#000000"


import re

SCALE_PATTERNS = [
    (r"1/8\"\s*=\s*1'[-\s]?0\"", 96.0),
    (r"1/4\"\s*=\s*1'[-\s]?0\"", 48.0),
    (r"3/16\"\s*=\s*1'[-\s]?0\"", 64.0),
    (r"3/8\"\s*=\s*1'[-\s]?0\"", 32.0),
    (r"1/2\"\s*=\s*1'[-\s]?0\"", 24.0),
    (r"1\"\s*=\s*1'[-\s]?0\"", 12.0),
    (r"1\"\s*=\s*10'", 1.2),
    (r"1\"\s*=\s*20'", 0.6),
    (r"NTS", None),
]


def _detect_scale(text_blocks: list, page) -> tuple:
    """Mirror of ai.pdf_extractor._detect_scale"""
    all_text = " ".join(b[4] for b in text_blocks if isinstance(b[4], str))
    for pattern, px_per_ft in SCALE_PATTERNS:
        if re.search(pattern, all_text, re.IGNORECASE):
            match = re.search(pattern, all_text, re.IGNORECASE)
            return px_per_ft, match.group(0) if match else ""
    return None, ""


class TestPtsToFt:
    def test_zero_origin(self):
        x_ft, y_ft = _pts_to_ft(0.0, 0.0, 792.0, 96.0)
        assert x_ft == 0.0
        assert y_ft > 0.0

    def test_x_axis_conversion(self):
        # 72 pts = 1 ft at 96 px/ft scale
        x_ft, _ = _pts_to_ft(72.0, 0.0, 0.0, 96.0)
        assert abs(x_ft - 1.0) < 0.001

    def test_y_axis_flipped(self):
        page_h = 720.0
        _, y_top = _pts_to_ft(0.0, 0.0, page_h, 96.0)
        _, y_bottom = _pts_to_ft(0.0, page_h, page_h, 96.0)
        assert y_top > y_bottom

    def test_zero_scale_returns_pixels(self):
        x, y = _pts_to_ft(72.0, 0.0, 0.0, 0.0)
        assert x == 96.0
        assert y == 0.0


class TestDetectScale:
    def _make_blocks(self, text: str):
        return [(0, 0, 100, 20, text, None, None)]

    def test_eighth_inch_scale(self):
        blocks = self._make_blocks("Scale: 1/8\" = 1'-0\"")
        px_per_ft, label = _detect_scale(blocks, None)
        assert px_per_ft == 96.0
        assert "1/8" in label

    def test_quarter_inch_scale(self):
        blocks = self._make_blocks("1/4\" = 1'-0\"")
        px_per_ft, label = _detect_scale(blocks, None)
        assert px_per_ft == 48.0

    def test_nts_returns_none(self):
        blocks = self._make_blocks("SCALE: NTS")
        px_per_ft, _ = _detect_scale(blocks, None)
        assert px_per_ft is None

    def test_no_scale_returns_none(self):
        blocks = self._make_blocks("General Notes")
        px_per_ft, label = _detect_scale(blocks, None)
        assert px_per_ft is None
        assert label == ""

    def test_case_insensitive(self):
        blocks = self._make_blocks("scale: 1/8\" = 1'-0\"")
        px_per_ft, _ = _detect_scale(blocks, None)
        assert px_per_ft == 96.0


class TestColorToHex:
    def test_black(self):
        assert _color_to_hex([0.0, 0.0, 0.0]) == "#000000"

    def test_white(self):
        assert _color_to_hex([1.0, 1.0, 1.0]) == "#ffffff"

    def test_red(self):
        assert _color_to_hex([1.0, 0.0, 0.0]) == "#ff0000"

    def test_blue(self):
        assert _color_to_hex([0.0, 0.0, 1.0]) == "#0000ff"

    def test_none_returns_black(self):
        assert _color_to_hex(None) == "#000000"

    def test_tuple_input(self):
        assert _color_to_hex((0.0, 1.0, 0.0)) == "#00ff00"
