"""
Raster image analysis for scanned drawings (PNG/JPG/TIFF).
Uses OpenCV for line detection and symbol region proposals.

Coordinates are stored as fractional values (0.0–1.0) of the page
dimensions when the drawing scale is unknown (NTS drawings or failed
scale detection). The drawing_analyzer caller is responsible for
converting to feet using the actual page dimensions once the scale is
known. When a px_per_ft value is provided, coordinates are converted
directly to feet.
"""
from __future__ import annotations

import math
import re
from dataclasses import dataclass, field
from pathlib import Path

import cv2
import numpy as np

from ai.drawing_analyzer import ExtractedGeometry

# Common architectural scale labels → decimal multiplier (inches per foot)
_SCALE_PATTERNS: list[tuple[re.Pattern, float]] = [
    (re.compile(r'1/8["\']?\s*=\s*1', re.I), 8 * 12),    # 1/8" = 1'-0"  → 96 px/ft at 1dpi
    (re.compile(r'1/4["\']?\s*=\s*1', re.I), 4 * 12),    # 1/4" = 1'-0"
    (re.compile(r'3/32["\']?\s*=\s*1', re.I), 32 / 3 * 12),
    (re.compile(r'3/16["\']?\s*=\s*1', re.I), 16 / 3 * 12),
    (re.compile(r'1/16["\']?\s*=\s*1', re.I), 16 * 12),
    (re.compile(r'1/2["\']?\s*=\s*1', re.I), 2 * 12),
    (re.compile(r'1["\']?\s*=\s*1', re.I), 12),           # 1" = 1'-0"
]


@dataclass
class RasterLine:
    x1: float
    y1: float
    x2: float
    y2: float
    length_px: float = field(init=False)

    def __post_init__(self):
        self.length_px = math.hypot(self.x2 - self.x1, self.y2 - self.y1)


def analyze_raster(
    image_path: str | Path,
    dpi: int = 150,
    page_number: int = 1,
    px_per_ft: float | None = None,
) -> ExtractedGeometry:
    """Extract geometry from a raster drawing image.

    Args:
        image_path: Path to the PNG/JPG/TIFF file.
        dpi: Image resolution in dots per inch.
        page_number: Page index (1-based) within the source document.
        px_per_ft: Known pixels-per-foot conversion from the drawing scale.
                   When None, we attempt to detect the scale from OCR text
                   in the title block. If detection fails, coordinates are
                   stored as fractions of the page dimensions (range 0–1)
                   with width_ft = height_ft = 0 to signal unknown scale.
    """
    img = cv2.imread(str(image_path))
    if img is None:
        raise ValueError(f"Cannot read image: {image_path}")

    h_px, w_px = img.shape[:2]
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

    # Binarize — HVAC drawings are typically dark lines on white background
    _, binary = cv2.threshold(gray, 200, 255, cv2.THRESH_BINARY_INV)

    # Morphological cleanup
    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (2, 2))
    binary = cv2.morphologyEx(binary, cv2.MORPH_CLOSE, kernel)

    lines = _detect_lines(binary)
    symbol_regions = _detect_symbol_candidates(binary, img, dpi)
    text_blocks = _detect_text_regions(gray)

    # ── Scale resolution ──────────────────────────────────────────────────
    resolved_px_per_ft = px_per_ft

    if resolved_px_per_ft is None:
        # Try to find a scale annotation in OCR'd text blocks
        for block in text_blocks:
            txt = block.get("text") or ""
            resolved_px_per_ft = _parse_scale_from_text(txt, dpi)
            if resolved_px_per_ft:
                break

    # Convert line coordinates
    polylines = []
    if resolved_px_per_ft and resolved_px_per_ft > 0:
        # Known scale: convert pixels → feet
        for ln in lines:
            polylines.append({
                "points": [
                    (ln.x1 / resolved_px_per_ft, ln.y1 / resolved_px_per_ft),
                    (ln.x2 / resolved_px_per_ft, ln.y2 / resolved_px_per_ft),
                ],
                "layer": "RASTER_LINE",
                "color": "#000000",
                "source": "raster",
            })
        width_ft = w_px / resolved_px_per_ft
        height_ft = h_px / resolved_px_per_ft
    else:
        # Unknown scale: store normalised fractions (0–1) so downstream code
        # can convert once the scale is established, rather than storing
        # pixel values which would be meaningless without the DPI context.
        for ln in lines:
            polylines.append({
                "points": [
                    (ln.x1 / w_px, ln.y1 / h_px),
                    (ln.x2 / w_px, ln.y2 / h_px),
                ],
                "layer": "RASTER_LINE",
                "color": "#000000",
                "source": "raster_normalized",  # flag for consumers
            })
        width_ft = 0.0   # 0 signals "unknown scale" to consumers
        height_ft = 0.0

    return ExtractedGeometry(
        page_number=page_number,
        width_ft=width_ft,
        height_ft=height_ft,
        scale_factor=resolved_px_per_ft or 0.0,
        polylines=polylines,
        text_elements=text_blocks,
        symbol_candidates=symbol_regions,
        width_px=w_px,
        height_px=h_px,
        dpi=dpi,
    )


def _parse_scale_from_text(text: str, dpi: int) -> float | None:
    """Return pixels-per-foot if a recognised scale annotation is found."""
    for pattern, inches_per_foot in _SCALE_PATTERNS:
        if pattern.search(text):
            return dpi * inches_per_foot
    return None


def _detect_lines(binary: np.ndarray) -> list[RasterLine]:
    """Probabilistic Hough line detection."""
    edges = cv2.Canny(binary, 50, 150, apertureSize=3)
    raw = cv2.HoughLinesP(
        edges,
        rho=1,
        theta=np.pi / 180,
        threshold=80,
        minLineLength=30,
        maxLineGap=10,
    )
    if raw is None:
        return []
    return [RasterLine(float(x1), float(y1), float(x2), float(y2))
            for x1, y1, x2, y2 in raw[:, 0]]


def _detect_symbol_candidates(
    binary: np.ndarray, color_img: np.ndarray, dpi: int
) -> list[dict]:
    """Return bounding boxes of closed contours that could be equipment symbols.

    Filters by size: symbols are typically 0.25"–3" on drawing paper.
    """
    min_px = int(0.25 * dpi)
    max_px = int(3.0 * dpi)

    contours, _ = cv2.findContours(binary, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    candidates = []
    for cnt in contours:
        x, y, w, h = cv2.boundingRect(cnt)
        if min_px <= w <= max_px and min_px <= h <= max_px:
            area = cv2.contourArea(cnt)
            hull_area = cv2.contourArea(cv2.convexHull(cnt))
            solidity = area / hull_area if hull_area > 0 else 0
            if solidity > 0.4:
                crop = color_img[y:y + h, x:x + w]
                candidates.append({
                    "bbox_px": [x, y, w, h],
                    "solidity": round(solidity, 3),
                    "crop": crop,
                })
    return candidates


def _detect_text_regions(gray: np.ndarray) -> list[dict]:
    """Detect dense text blobs (title block, schedules) via morphological dilation.

    Runs easyocr on each region to extract the actual text content.
    """
    _, bw = cv2.threshold(gray, 180, 255, cv2.THRESH_BINARY_INV)
    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (20, 5))
    dilated = cv2.dilate(bw, kernel)
    contours, _ = cv2.findContours(dilated, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    regions = []
    for cnt in contours:
        x, y, w, h = cv2.boundingRect(cnt)
        if w > 50 and h > 8:
            regions.append({
                "bbox_px": [x, y, w, h],
                "text": None,
                "_crop": gray[y:y + h, x:x + w],
            })

    if not regions:
        return regions

    try:
        import easyocr
        reader = easyocr.Reader(["en"], gpu=False, verbose=False)
        for region in regions:
            crop = region.pop("_crop")
            results = reader.readtext(crop, detail=0, paragraph=True)
            region["text"] = " ".join(results).strip() if results else None
    except Exception:
        for region in regions:
            region.pop("_crop", None)

    return regions
