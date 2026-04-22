"""
PDF vector geometry extractor using PyMuPDF.
Extracts lines, polylines, text, and computes real-world scale.
"""
import re
import fitz  # PyMuPDF
from ai.drawing_analyzer import ExtractedGeometry
from ai.layer_classifier import classify_layer_from_color


# Common scale patterns in title blocks
SCALE_PATTERNS = [
    (r"1/8\"\s*=\s*1'[-\s]?0\"", 96.0),    # 1/8" = 1'-0" → 96 px/ft at 96dpi
    (r"1/4\"\s*=\s*1'[-\s]?0\"", 48.0),
    (r"3/16\"\s*=\s*1'[-\s]?0\"", 64.0),
    (r"3/8\"\s*=\s*1'[-\s]?0\"", 32.0),
    (r"1/2\"\s*=\s*1'[-\s]?0\"", 24.0),
    (r"1\"\s*=\s*1'[-\s]?0\"", 12.0),
    (r"1\"\s*=\s*10'", 1.2),
    (r"1\"\s*=\s*20'", 0.6),
    (r"NTS", None),  # Not to scale
]


def extract_pdf(file_bytes: bytes) -> list[ExtractedGeometry]:
    doc = fitz.open(stream=file_bytes, filetype="pdf")
    results = []

    for page_num in range(len(doc)):
        page = doc[page_num]
        geom = ExtractedGeometry(page_number=page_num + 1)

        # Detect scale from text
        text_blocks = page.get_text("blocks")
        scale_px_per_ft, scale_label = _detect_scale(text_blocks, page)
        geom.scale_label = scale_label

        # Page dimensions
        rect = page.rect
        page_width_pts = rect.width
        page_height_pts = rect.height

        if scale_px_per_ft:
            # Convert from PDF points (72 pts/inch) to feet
            pts_per_ft = scale_px_per_ft * 72 / 96  # approximate
            geom.scale_factor = scale_px_per_ft
            geom.width_ft = page_width_pts / pts_per_ft if pts_per_ft else 0
            geom.height_ft = page_height_pts / pts_per_ft if pts_per_ft else 0
        else:
            # Default assumption: 1/8" = 1'-0" (most common MEP scale)
            pts_per_ft = 9.0
            geom.scale_factor = 96.0
            geom.width_ft = page_width_pts / pts_per_ft
            geom.height_ft = page_height_pts / pts_per_ft

        # Extract vector paths
        paths = page.get_drawings()
        for path in paths:
            color = path.get("color") or path.get("fill")
            layer = classify_layer_from_color(color)

            for item in path["items"]:
                if item[0] == "l":  # line
                    x1, y1 = _pts_to_ft(item[1].x, item[1].y, page_height_pts, geom.scale_factor)
                    x2, y2 = _pts_to_ft(item[2].x, item[2].y, page_height_pts, geom.scale_factor)
                    geom.lines.append({
                        "x1": x1, "y1": y1, "x2": x2, "y2": y2,
                        "layer": layer,
                        "linewidth": path.get("width", 1.0),
                        "color": _color_to_hex(color),
                    })
                elif item[0] == "qu":  # quad/rect
                    pts = [_pts_to_ft(p.x, p.y, page_height_pts, geom.scale_factor) for p in item[1]]
                    geom.polylines.append({
                        "points": [{"x": p[0], "y": p[1]} for p in pts],
                        "layer": layer,
                        "closed": True,
                        "color": _color_to_hex(color),
                    })
                elif item[0] == "re":  # rect
                    r = item[1]
                    tl = _pts_to_ft(r.x0, r.y0, page_height_pts, geom.scale_factor)
                    tr = _pts_to_ft(r.x1, r.y0, page_height_pts, geom.scale_factor)
                    br = _pts_to_ft(r.x1, r.y1, page_height_pts, geom.scale_factor)
                    bl = _pts_to_ft(r.x0, r.y1, page_height_pts, geom.scale_factor)
                    geom.polylines.append({
                        "points": [{"x": p[0], "y": p[1]} for p in [tl, tr, br, bl]],
                        "layer": layer,
                        "closed": True,
                        "color": _color_to_hex(color),
                    })

        # Extract text
        for block in text_blocks:
            x0, y0, x1, y1 = block[:4]
            text = block[4].strip()
            if not text:
                continue
            cx, cy = _pts_to_ft((x0 + x1) / 2, (y0 + y1) / 2, page_height_pts, geom.scale_factor)
            geom.text_elements.append({
                "x": cx, "y": cy,
                "text": text,
                "rotation": 0,
                "height": (y1 - y0) / geom.scale_factor if geom.scale_factor else 0,
                "layer": "text",
            })

        results.append(geom)

    doc.close()
    return results


def _pts_to_ft(x_pts: float, y_pts: float, page_height_pts: float, scale_px_per_ft: float) -> tuple[float, float]:
    """Convert PDF points to real-world feet. Y-axis is flipped (PDF origin is bottom-left)."""
    pts_per_inch = 72.0
    px_per_inch = 96.0
    px_per_pt = px_per_inch / pts_per_inch
    x_px = x_pts * px_per_pt
    y_px = (page_height_pts - y_pts) * px_per_pt  # flip Y
    if scale_px_per_ft and scale_px_per_ft > 0:
        return x_px / scale_px_per_ft, y_px / scale_px_per_ft
    return x_px, y_px


def _detect_scale(text_blocks: list, page) -> tuple[float | None, str]:
    all_text = " ".join(b[4] for b in text_blocks if isinstance(b[4], str))
    for pattern, px_per_ft in SCALE_PATTERNS:
        if re.search(pattern, all_text, re.IGNORECASE):
            match = re.search(pattern, all_text, re.IGNORECASE)
            return px_per_ft, match.group(0) if match else ""
    return None, ""


def _color_to_hex(color) -> str:
    if not color:
        return "#000000"
    if isinstance(color, (list, tuple)) and len(color) == 3:
        r, g, b = [int(c * 255) for c in color]
        return f"#{r:02x}{g:02x}{b:02x}"
    return "#000000"
