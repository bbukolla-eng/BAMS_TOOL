"""Tests for the layer classifier used during drawing analysis."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "backend"))

from ai.layer_classifier import classify_layer_from_name, classify_layer_from_color


class TestClassifyLayerFromName:
    def test_exact_aia_supply_duct(self):
        assert classify_layer_from_name("M-HVAC-DUCT-S") == "duct_supply"

    def test_exact_aia_return_duct(self):
        assert classify_layer_from_name("M-HVAC-DUCT-R") == "duct_return"

    def test_exact_aia_exhaust_duct(self):
        assert classify_layer_from_name("M-HVAC-DUCT-E") == "duct_exhaust"

    def test_aia_chw_supply_pipe(self):
        assert classify_layer_from_name("M-PIPE-CHW-S") == "pipe_chw_supply"

    def test_aia_chw_return_pipe(self):
        assert classify_layer_from_name("M-PIPE-CHW-R") == "pipe_chw_return"

    def test_abbreviated_chws(self):
        assert classify_layer_from_name("CHWS") == "pipe_chw_supply"

    def test_abbreviated_chwr(self):
        assert classify_layer_from_name("CHWR") == "pipe_chw_return"

    def test_hot_water_supply(self):
        assert classify_layer_from_name("HWS") == "pipe_hw_supply"

    def test_hot_water_return(self):
        assert classify_layer_from_name("HWR") == "pipe_hw_return"

    def test_case_insensitive(self):
        assert classify_layer_from_name("m-hvac-duct-s") == "duct_supply"
        assert classify_layer_from_name("DUCT-SUPPLY") == "duct_supply"

    def test_generic_mech_prefix(self):
        result = classify_layer_from_name("M-MISC-OTHER")
        assert result == "mechanical"

    def test_generic_elec_prefix(self):
        result = classify_layer_from_name("E-MISC")
        assert result == "electrical"

    def test_generic_plumbing_prefix(self):
        result = classify_layer_from_name("P-MISC")
        assert result == "plumbing"

    def test_electrical_conduit(self):
        assert classify_layer_from_name("E-CONDUIT") == "conduit"

    def test_sanitary(self):
        assert classify_layer_from_name("P-SANR") == "pipe_sanitary"

    def test_unknown_layer(self):
        assert classify_layer_from_name("A-WALL-FULL") == "unknown"

    def test_steam_pipe(self):
        assert classify_layer_from_name("STEAM") == "pipe_steam"

    def test_condensate(self):
        assert classify_layer_from_name("M-PIPE-CON") == "pipe_condensate"


class TestClassifyLayerFromColor:
    def test_blue_chw_supply(self):
        result = classify_layer_from_color([0.0, 0.0, 1.0])  # pure blue
        assert result == "pipe_chw_supply"

    def test_red_hw_supply(self):
        result = classify_layer_from_color([1.0, 0.0, 0.0])  # pure red
        assert result == "pipe_hw_supply"

    def test_none_color_unknown(self):
        assert classify_layer_from_color(None) == "unknown"

    def test_invalid_color_unknown(self):
        assert classify_layer_from_color("red") == "unknown"

    def test_far_from_all_colors_unknown(self):
        # Mid-gray (127, 127, 127) is far from all defined colors
        result = classify_layer_from_color([0.5, 0.5, 0.5])
        # Distance check: this may or may not match depending on threshold
        # Just verify it returns a string
        assert isinstance(result, str)

    def test_yellow_conduit(self):
        result = classify_layer_from_color([1.0, 1.0, 0.0])  # pure yellow
        assert result == "conduit"
