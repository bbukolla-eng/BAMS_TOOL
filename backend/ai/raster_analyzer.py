"""
Raster image analysis for scanned drawings (PNG/JPG/TIFF).
Uses OpenCV for line detection and symbol region proposals.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

import cv2
import numpy as np

from ai.drawing_analyzer import ExtractedGeometry


@dataclass
class RasterLine:
    x1: float
    y1: float
    x2: float
    y2: float
    length_px: float = field(init=False)

    def __post_init__(self):
        self.length_px = math.hypot(self.x2 - self.x1, self.y2 - self.y1)


def analyze_raster(image_path: str | Path, dpi: int = 150, page_number: int = 1) -> ExtractedGeometry:
    """
    Extract geometry from a raster drawing image.
    Returns ExtractedGeometry with polylines in pixel coordinates
    (scale_factor must be set externally from known drawing scale).
    """
    img = cv2.imread(str(image_path))
    if img is None:
        raise ValueError(f"Cannot read image: {image_path}")

    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

    # Binarize — HVAC drawings are typically dark lines on white background
    _, binary = cv2.threshold(gray, 200, 255, cv2.THRESH_BINARY_INV)

    # Morphological cleanup
    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (2, 2))
    binary = cv2.morphologyEx(binary, cv2.MORPH_CLOSE, kernel)

    lines = _detect_lines(binary)
    symbol_regions = _detect_symbol_candidates(binary, img, dpi)
    text_blocks = _detect_text_regions(gray)

    px_per_ft = dpi * 12  # placeholder; caller should override with known scale

    polylines = []
    for ln in lines:
        polylines.append({
            "points": [(ln.x1 / px_per_ft, ln.y1 / px_per_ft),
                       (ln.x2 / px_per_ft, ln.y2 / px_per_ft)],
            "layer": "RASTER_LINE",
            "color": "#000000",
            "source": "raster",
        })

    return ExtractedGeometry(
        page_number=page_number,
        polylines=polylines,
        text_elements=text_blocks,
        symbol_candidates=symbol_regions,
        width_px=img.shape[1],
        height_px=img.shape[0],
        dpi=dpi,
    )


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
    """
    Return bounding boxes of closed contours that could be equipment symbols.
    Filter by size: symbols are typically 0.25"–3" on drawing paper.
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
    """
    Detect dense text blobs (title block, schedules) using morphological dilation.
    Returns approximate bounding boxes; OCR is handled downstream.
    """
    _, bw = cv2.threshold(gray, 180, 255, cv2.THRESH_BINARY_INV)
    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (20, 5))
    dilated = cv2.dilate(bw, kernel)
    contours, _ = cv2.findContours(dilated, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    regions = []
    for cnt in contours:
        x, y, w, h = cv2.boundingRect(cnt)
        if w > 50 and h > 8:
            regions.append({"bbox_px": [x, y, w, h], "text": None})
    return regions
