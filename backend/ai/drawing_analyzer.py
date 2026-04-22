"""
Core drawing analysis pipeline.
Entry point for both PDF vector extraction and raster image analysis.
Dispatches to the appropriate sub-analyzer based on file type.
"""
import logging
from dataclasses import dataclass, field
from pathlib import Path

log = logging.getLogger(__name__)


@dataclass
class ExtractedGeometry:
    """Normalized drawing geometry in real-world feet."""
    page_number: int = 1
    width_ft: float = 0.0
    height_ft: float = 0.0
    scale_factor: float = 1.0      # pixels per foot (for raster)
    scale_label: str = ""          # "1/8\" = 1'-0\""
    lines: list[dict] = field(default_factory=list)
    polylines: list[dict] = field(default_factory=list)
    text_elements: list[dict] = field(default_factory=list)
    blocks: list[dict] = field(default_factory=list)
    symbol_candidates: list[dict] = field(default_factory=list)  # raster bounding boxes
    width_px: int = 0
    height_px: int = 0
    dpi: int = 0


@dataclass
class AnalysisResult:
    drawing_id: int
    page_number: int
    symbols: list[dict] = field(default_factory=list)
    material_runs: list[dict] = field(default_factory=list)
    scale_ft: float = 0.0
    scale_label: str = ""
    width_ft: float = 0.0
    height_ft: float = 0.0
    errors: list[str] = field(default_factory=list)


async def analyze_drawing(drawing_id: int, file_bytes: bytes, file_type: str) -> list[AnalysisResult]:
    """
    Main entry point. Returns one AnalysisResult per page.
    """
    if file_type == "pdf":
        from ai.pdf_extractor import extract_pdf
        geometries = extract_pdf(file_bytes)
    elif file_type in ("dxf", "dwg"):
        from ai.dxf_extractor import extract_dxf
        geometries = extract_dxf(file_bytes)
    else:
        import tempfile, os
        from ai.raster_analyzer import analyze_raster
        with tempfile.NamedTemporaryFile(suffix=f".{file_type}", delete=False) as tmp:
            tmp.write(file_bytes)
            tmp_path = tmp.name
        try:
            geometries = [analyze_raster(tmp_path)]
        finally:
            os.unlink(tmp_path)

    results = []
    for geom in geometries:
        result = AnalysisResult(drawing_id=drawing_id, page_number=geom.page_number)
        result.scale_ft = geom.scale_factor
        result.scale_label = geom.scale_label
        result.width_ft = geom.width_ft
        result.height_ft = geom.height_ft

        # Run material run tracing on vector geometry
        from ai.run_tracer import trace_material_runs
        runs = trace_material_runs(geom)
        result.material_runs = runs

        # Run symbol detection on raster representation
        from ai.symbol_detector import detect_symbols
        symbols = await detect_symbols(drawing_id, geom, file_bytes)
        result.symbols = symbols

        results.append(result)

    return results
