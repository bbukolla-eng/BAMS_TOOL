"""Tests for the Division 23 HVAC symbol library."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "backend"))

from ai.div23.symbols import HVAC_SYMBOLS, MATERIAL_RUN_TYPES, get_symbol_def, SymbolDefinition


class TestHVACSymbols:
    def test_ahu_defined(self):
        assert "ahu" in HVAC_SYMBOLS

    def test_ahu_csi_code(self):
        assert HVAC_SYMBOLS["ahu"].csi_code == "23 73 13"

    def test_ahu_unit_ea(self):
        assert HVAC_SYMBOLS["ahu"].unit == "EA"

    def test_vav_box_defined(self):
        assert "vav_box" in HVAC_SYMBOLS

    def test_fire_damper_defined(self):
        assert "fire_damper" in HVAC_SYMBOLS

    def test_all_symbols_have_csi_code(self):
        for key, sym in HVAC_SYMBOLS.items():
            assert sym.csi_code, f"{key} missing CSI code"

    def test_all_symbols_have_description(self):
        for key, sym in HVAC_SYMBOLS.items():
            assert sym.description, f"{key} missing description"

    def test_all_symbols_have_unit(self):
        for key, sym in HVAC_SYMBOLS.items():
            assert sym.unit in ("EA", "LF", "SF", "TON"), f"{key} has unexpected unit"

    def test_all_symbols_count_method_each(self):
        # All equipment symbols should use "each" counting
        equipment_types = {k for k, v in HVAC_SYMBOLS.items() if v.category == "equipment"}
        for key in equipment_types:
            assert HVAC_SYMBOLS[key].count_method == "each", f"{key} should use count_method=each"

    def test_waste_factor_default(self):
        assert HVAC_SYMBOLS["ahu"].waste_factor == 0.05

    def test_diffuser_supply_defined(self):
        assert "diffuser_supply" in HVAC_SYMBOLS

    def test_chiller_defined(self):
        sym = HVAC_SYMBOLS.get("chiller")
        assert sym is not None
        assert sym.system == "Chilled Water"

    def test_pump_csi_code(self):
        assert HVAC_SYMBOLS["pump"].csi_code == "23 21 23"


class TestGetSymbolDef:
    def test_returns_definition_for_known(self):
        sym = get_symbol_def("ahu")
        assert sym is not None
        assert isinstance(sym, SymbolDefinition)
        assert sym.symbol_type == "ahu"

    def test_returns_none_for_unknown(self):
        assert get_symbol_def("nonexistent_type") is None

    def test_returns_none_for_empty_string(self):
        assert get_symbol_def("") is None


class TestMaterialRunTypes:
    def test_duct_supply_defined(self):
        assert "duct_supply" in MATERIAL_RUN_TYPES

    def test_all_have_csi_code(self):
        for key, entry in MATERIAL_RUN_TYPES.items():
            assert "csi_code" in entry, f"{key} missing csi_code"

    def test_all_have_unit_lf(self):
        for key, entry in MATERIAL_RUN_TYPES.items():
            assert entry["unit"] == "LF", f"{key} should have LF unit"

    def test_pipe_chw_supply_csi(self):
        assert MATERIAL_RUN_TYPES["pipe_chw_supply"]["csi_code"] == "23 21 13"

    def test_conduit_defined(self):
        assert "conduit" in MATERIAL_RUN_TYPES
        assert MATERIAL_RUN_TYPES["conduit"]["category"] == "conduit"

    def test_refrigerant_pipe_defined(self):
        assert "pipe_refrigerant" in MATERIAL_RUN_TYPES
