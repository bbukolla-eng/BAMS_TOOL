"""Tests for the material run tracer that connects line segments into runs."""
import sys
import math
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "backend"))

from ai.run_tracer import trace_material_runs, _snap, _infer_size_from_layer
from ai.drawing_analyzer import ExtractedGeometry


def make_geom(**kwargs) -> ExtractedGeometry:
    return ExtractedGeometry(page_number=1, **kwargs)


class TestSnapFunction:
    def test_snaps_to_tolerance_grid(self):
        # Points that round to the same 0.5ft grid cell should snap equal.
        # 0.2 / 0.5 = 0.4 → round(0.4) = 0 → 0.0; same for both points.
        p1 = (0.0, 0.0)
        p2 = (0.2, 0.1)
        assert _snap(p1) == _snap(p2)

    def test_distant_points_dont_snap(self):
        p1 = (0.0, 0.0)
        p2 = (1.5, 1.5)
        assert _snap(p1) != _snap(p2)


class TestInferSizeFromLayer:
    def test_duct_rectangular_size(self):
        result = _infer_size_from_layer("DUCT-24X12", "duct_supply")
        assert result == "24x12"

    def test_duct_round_size(self):
        result = _infer_size_from_layer("DUCT-12RD", "duct_supply")
        assert result == '12" round'

    def test_pipe_size_inches(self):
        result = _infer_size_from_layer("PIPE-CHW-4IN", "pipe_chw_supply")
        assert result == '4"'

    def test_no_size_in_layer(self):
        result = _infer_size_from_layer("M-HVAC-DUCT-S", "duct_supply")
        assert result is None


class TestTraceMaterialRuns:
    def test_single_line_becomes_run(self):
        geom = make_geom(lines=[
            {"x1": 0.0, "y1": 0.0, "x2": 10.0, "y2": 0.0, "layer": "duct_supply"},
        ])
        runs = trace_material_runs(geom)
        assert len(runs) == 1
        assert runs[0]["material_type"] == "duct_supply"
        assert abs(runs[0]["length_ft"] - 10.0) < 0.01

    def test_unknown_layer_skipped(self):
        geom = make_geom(lines=[
            {"x1": 0.0, "y1": 0.0, "x2": 5.0, "y2": 0.0, "layer": "unknown"},
        ])
        runs = trace_material_runs(geom)
        assert runs == []

    def test_two_connected_lines_merge(self):
        # Two collinear segments sharing an endpoint
        geom = make_geom(lines=[
            {"x1": 0.0, "y1": 0.0, "x2": 5.0, "y2": 0.0, "layer": "pipe_chw_supply"},
            {"x1": 5.0, "y1": 0.0, "x2": 10.0, "y2": 0.0, "layer": "pipe_chw_supply"},
        ])
        runs = trace_material_runs(geom)
        total = sum(r["length_ft"] for r in runs)
        assert abs(total - 10.0) < 0.1

    def test_short_segments_below_half_foot_ignored(self):
        geom = make_geom(lines=[
            {"x1": 0.0, "y1": 0.0, "x2": 0.3, "y2": 0.0, "layer": "duct_supply"},
        ])
        runs = trace_material_runs(geom)
        assert runs == []

    def test_different_material_types_separate_runs(self):
        geom = make_geom(lines=[
            {"x1": 0.0, "y1": 0.0, "x2": 10.0, "y2": 0.0, "layer": "duct_supply"},
            {"x1": 0.0, "y1": 5.0, "x2": 10.0, "y2": 5.0, "layer": "pipe_chw_supply"},
        ])
        runs = trace_material_runs(geom)
        types = {r["material_type"] for r in runs}
        assert "duct_supply" in types
        assert "pipe_chw_supply" in types

    def test_polyline_edges_create_runs(self):
        geom = make_geom(
            lines=[],
            polylines=[{
                "layer": "duct_supply",
                "points": [
                    {"x": 0.0, "y": 0.0},
                    {"x": 5.0, "y": 0.0},
                    {"x": 5.0, "y": 5.0},
                ],
                "closed": False,
            }],
        )
        runs = trace_material_runs(geom)
        assert len(runs) >= 1
        total_len = sum(r["length_ft"] for r in runs)
        assert abs(total_len - 10.0) < 0.2

    def test_run_confidence_non_unknown(self):
        geom = make_geom(lines=[
            {"x1": 0.0, "y1": 0.0, "x2": 10.0, "y2": 0.0, "layer": "duct_supply"},
        ])
        runs = trace_material_runs(geom)
        assert runs[0]["confidence"] == 0.90

    def test_detection_source_vector(self):
        geom = make_geom(lines=[
            {"x1": 0.0, "y1": 0.0, "x2": 10.0, "y2": 0.0, "layer": "pipe_hw_supply"},
        ])
        runs = trace_material_runs(geom)
        assert runs[0]["detection_source"] == "vector"
