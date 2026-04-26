"""Fitting detection in run_tracer — counts elbows, tees, transitions from
the connectivity graph of detected line segments."""
import sys
from dataclasses import dataclass, field
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "backend"))

from ai.run_tracer import (
    _bend_angle_deg,
    _size_token,
    trace_material_runs,
)


@dataclass
class _Geom:
    page_number: int = 1
    lines: list = field(default_factory=list)
    polylines: list = field(default_factory=list)
    text_elements: list = field(default_factory=list)
    blocks: list = field(default_factory=list)
    scale_factor: float | None = None
    width_ft: float | None = None
    height_ft: float | None = None


def _line(x1, y1, x2, y2, layer="duct_supply", layer_name="DUCT-SUP-12X8"):
    return {"x1": x1, "y1": y1, "x2": x2, "y2": y2, "layer": layer, "layer_name": layer_name}


class TestBendAngle:
    def test_straight_line_zero_deflection(self):
        # n1 at (1,0), vertex at (0,0), n2 at (-1,0) — perfectly straight
        assert _bend_angle_deg((0, 0), (1, 0), (-1, 0)) == 0.0

    def test_ninety_degree_bend(self):
        # n1 at (1,0), vertex at (0,0), n2 at (0,1) — 90° corner
        assert abs(_bend_angle_deg((0, 0), (1, 0), (0, 1)) - 90.0) < 0.001

    def test_forty_five_degree_bend(self):
        # Real 45° elbow geometry: duct comes in from east (n1 at (1,0)),
        # leaves toward NW (n2 at (-1, 1)). Interior between the two
        # outgoing vectors is 135°; deflection from straight is 45°.
        angle = _bend_angle_deg((0, 0), (1, 0), (-1, 1))
        assert abs(angle - 45.0) < 0.001

    def test_zero_length_returns_zero(self):
        assert _bend_angle_deg((0, 0), (0, 0), (1, 0)) == 0.0


class TestFittingDetection:
    def test_straight_run_no_fittings(self):
        # Two collinear segments → no elbows, no tees
        geom = _Geom(lines=[_line(0, 0, 5, 0), _line(5, 0, 10, 0)])
        runs = trace_material_runs(geom)
        assert len(runs) == 1
        assert runs[0]["fittings"] == {
            "elbow_45": 0, "elbow_90": 0, "tee": 0, "cross": 0, "transition": 0
        }

    def test_l_shaped_run_counts_one_elbow_90(self):
        geom = _Geom(lines=[_line(0, 0, 5, 0), _line(5, 0, 5, 5)])
        runs = trace_material_runs(geom)
        assert len(runs) == 1
        f = runs[0]["fittings"]
        assert f["elbow_90"] == 1
        assert f["elbow_45"] == 0
        assert f["tee"] == 0

    def test_offset_run_counts_two_elbow_90(self):
        # 0,0 → 5,0 → 5,5 → 10,5  : two corners
        geom = _Geom(lines=[
            _line(0, 0, 5, 0),
            _line(5, 0, 5, 5),
            _line(5, 5, 10, 5),
        ])
        runs = trace_material_runs(geom)
        assert len(runs) == 1
        assert runs[0]["fittings"]["elbow_90"] == 2

    def test_45_degree_bend_counts_elbow_45(self):
        # 0,0 → 5,0 → 10,5 (45° corner at 5,0)
        geom = _Geom(lines=[_line(0, 0, 5, 0), _line(5, 0, 10, 5)])
        runs = trace_material_runs(geom)
        assert len(runs) == 1
        f = runs[0]["fittings"]
        assert f["elbow_45"] == 1
        assert f["elbow_90"] == 0

    def test_tee_branch_counts_one_tee(self):
        # T-shape: long horizontal main with a vertical branch in the middle
        geom = _Geom(lines=[
            _line(0, 0, 10, 0),  # main split mid-way
            _line(10, 0, 20, 0),
            _line(10, 0, 10, 10),  # branch
        ])
        runs = trace_material_runs(geom)
        assert len(runs) == 1
        assert runs[0]["fittings"]["tee"] == 1

    def test_cross_counts_one_cross(self):
        geom = _Geom(lines=[
            _line(-5, 0, 0, 0),
            _line(0, 0, 5, 0),
            _line(0, -5, 0, 0),
            _line(0, 0, 0, 5),
        ])
        runs = trace_material_runs(geom)
        assert len(runs) == 1
        assert runs[0]["fittings"]["cross"] == 1

    def test_transition_when_adjacent_layers_have_different_sizes(self):
        # Same material type, but different layer-encoded sizes ⇒ transition
        geom = _Geom(lines=[
            _line(0, 0, 5, 0, layer="duct_supply", layer_name="M-DUCT-SUP-12X8"),
            _line(5, 0, 10, 0, layer="duct_supply", layer_name="M-DUCT-SUP-10X8"),
        ])
        runs = trace_material_runs(geom)
        assert runs[0]["fittings"]["transition"] == 1

    def test_two_separate_l_runs_dont_double_count(self):
        # Two disconnected L-runs → exactly two elbows total, one per component
        geom = _Geom(lines=[
            _line(0, 0, 5, 0), _line(5, 0, 5, 5),
            _line(20, 20, 25, 20), _line(25, 20, 25, 25),
        ])
        runs = trace_material_runs(geom)
        assert len(runs) == 2
        total_elbows = sum(r["fittings"]["elbow_90"] for r in runs)
        assert total_elbows == 2


class TestSizeTokenExtraction:
    def test_rectangular(self):
        assert _size_token("M-DUCT-SUP-12X8") == "12x8"

    def test_round_inch(self):
        assert _size_token("PIPE-CHW-4IN") == "4\""

    def test_round_rd_suffix(self):
        assert _size_token("DUCT-RA-10RD") == "10\""

    def test_no_size_returns_none(self):
        assert _size_token("DUCT-SUP") is None
        assert _size_token(None) is None
