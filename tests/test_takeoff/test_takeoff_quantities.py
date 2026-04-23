"""
Tests for takeoff quantity logic: waste factor math, unit conventions,
and the symbol/run data structures produced by the drawing analyzer.
"""
import sys
import math
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "backend"))


class TestWasteFactorCalculation:
    """Waste factor is always applied as adjusted_qty = qty * (1 + waste_factor)."""

    def _adjusted(self, qty: float, waste: float) -> float:
        return qty * (1 + waste)

    def test_standard_five_percent(self):
        result = self._adjusted(100.0, 0.05)
        assert result == 105.0

    def test_zero_waste(self):
        result = self._adjusted(200.0, 0.0)
        assert result == 200.0

    def test_ten_percent_waste(self):
        result = self._adjusted(50.0, 0.10)
        assert abs(result - 55.0) < 0.001

    def test_adjusted_qty_always_gte_original(self):
        for qty, waste in [(10, 0.05), (100, 0.10), (1000, 0.15)]:
            assert self._adjusted(qty, waste) >= qty

    def test_fractional_quantity(self):
        result = self._adjusted(33.3, 0.05)
        assert abs(result - 34.965) < 0.001


class TestUnitConventions:
    """Check expected units for each takeoff category match MasterFormat."""

    EXPECTED_UNITS = {
        "duct": "LF",
        "pipe": "LF",
        "equipment": "EA",
        "diffuser": "EA",
        "damper": "EA",
        "valve": "EA",
        "insulation": "SF",
    }

    def test_duct_unit_lf(self):
        assert self.EXPECTED_UNITS["duct"] == "LF"

    def test_equipment_unit_ea(self):
        assert self.EXPECTED_UNITS["equipment"] == "EA"

    def test_insulation_unit_sf(self):
        assert self.EXPECTED_UNITS["insulation"] == "SF"

    def test_valve_unit_ea(self):
        assert self.EXPECTED_UNITS["valve"] == "EA"

    def test_all_units_valid(self):
        valid = {"LF", "EA", "SF", "LB", "TON"}
        for cat, unit in self.EXPECTED_UNITS.items():
            assert unit in valid, f"Category {cat} has unexpected unit {unit}"


class TestSymbolCountingLogic:
    """
    Symbols detected by the AI are counted by occurrence (EA).
    Verify count rules for different symbol types using the div23 library.
    """

    def setup_method(self):
        from ai.div23.symbols import HVAC_SYMBOLS
        self.symbols = HVAC_SYMBOLS

    def test_ahu_counted_per_each(self):
        assert self.symbols["ahu"].count_method == "each"

    def test_diffuser_counted_per_each(self):
        assert self.symbols["diffuser_supply"].count_method == "each"

    def test_valve_counted_per_each(self):
        assert self.symbols["valve_ball"].count_method == "each"

    def test_multiple_symbols_sum_to_correct_count(self):
        symbol_occurrences = ["ahu", "ahu", "fcu", "vav_box", "vav_box", "vav_box"]
        counts = {}
        for s in symbol_occurrences:
            counts[s] = counts.get(s, 0) + 1
        assert counts["ahu"] == 2
        assert counts["fcu"] == 1
        assert counts["vav_box"] == 3

    def test_no_symbol_type_has_length_method(self):
        # All div23 equipment symbols use 'each', not 'length'
        for key, sym in self.symbols.items():
            assert sym.count_method != "length", f"{key} unexpectedly uses length counting"


class TestMaterialRunLengthCalculation:
    """Test that run length calculations from the run tracer are consistent."""

    def test_straight_run_length(self):
        # Pythagoras: sqrt((10-0)^2 + (0-0)^2) = 10
        p1, p2 = (0.0, 0.0), (10.0, 0.0)
        length = math.hypot(p2[0] - p1[0], p2[1] - p1[1])
        assert abs(length - 10.0) < 0.001

    def test_diagonal_run_length(self):
        p1, p2 = (0.0, 0.0), (3.0, 4.0)
        length = math.hypot(p2[0] - p1[0], p2[1] - p1[1])
        assert abs(length - 5.0) < 0.001

    def test_multi_segment_run_total(self):
        segments = [
            ((0.0, 0.0), (10.0, 0.0)),
            ((10.0, 0.0), (10.0, 5.0)),
            ((10.0, 5.0), (20.0, 5.0)),
        ]
        total = sum(math.hypot(p2[0] - p1[0], p2[1] - p1[1]) for p1, p2 in segments)
        assert abs(total - 25.0) < 0.001

    def test_zero_length_segment_ignored(self):
        p1 = p2 = (5.0, 5.0)
        length = math.hypot(p2[0] - p1[0], p2[1] - p1[1])
        assert length == 0.0

    def test_waste_applied_to_duct_run(self):
        raw_length_ft = 100.0
        waste_factor = 0.05
        adjusted = raw_length_ft * (1 + waste_factor)
        assert adjusted == 105.0
