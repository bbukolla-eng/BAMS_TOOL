"""
Tests for the manufacturer line-list importer (CSV/XLSX) — header detection,
value parsing, and upsert logic. These tests don't touch the database; they
exercise the pure parsing helpers.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "backend"))
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "scripts"))

from import_price_book import (
    _canonical,
    _normalize,
    _parse_float,
    _parse_money,
    _rows_with_headers,
    parse_buffer,
)


class TestHeaderAliases:
    """Each manufacturer formats their line list differently; the importer
    must accept common variants for the same logical column."""

    def test_recognises_description_synonyms(self):
        for label in ["Description", "DESCRIPTION", "item description", "Product"]:
            assert _canonical(label) == "description", label

    def test_recognises_csi_synonyms(self):
        for label in ["CSI", "CSI Code", "Spec Section", "MasterFormat"]:
            assert _canonical(label) == "csi_code", label

    def test_recognises_model_synonyms(self):
        for label in ["Model", "Model Number", "Part No", "SKU", "Catalog Number"]:
            assert _canonical(label) == "model_number", label

    def test_recognises_price_synonyms(self):
        for label in ["Price", "List Price", "Unit Cost", "$", "USD"]:
            assert _canonical(label) == "material_unit_cost", label

    def test_recognises_unit_synonyms(self):
        for label in ["Unit", "UOM", "U/M", "Unit of Measure"]:
            assert _canonical(label) == "unit", label

    def test_unknown_header_returns_empty(self):
        assert _canonical("Random Column") == ""

    def test_punctuation_tolerance(self):
        assert _canonical("CSI-CODE") == "csi_code"
        assert _canonical("Model_Number") == "model_number"


class TestValueParsing:
    """Manufacturer line lists smuggle currency formatting, dashes, and
    parenthetical negatives. The parser must clean these up."""

    def test_parses_dollar_signs(self):
        assert _parse_money("$1,250.00") == 1250.0

    def test_parses_thousands_separator(self):
        assert _parse_money("28,500") == 28500.0

    def test_parses_parenthetical_negative(self):
        assert _parse_money("(15.50)") == -15.50

    def test_blank_returns_none(self):
        assert _parse_money("") is None
        assert _parse_money(None) is None
        assert _parse_money("   ") is None

    def test_garbage_returns_none(self):
        assert _parse_money("CALL FOR PRICE") is None
        assert _parse_money("TBD") is None

    def test_float_parses_plain(self):
        assert _parse_float("0.25") == 0.25
        assert _parse_float("3") == 3.0

    def test_float_blank_returns_none(self):
        assert _parse_float("") is None
        assert _parse_float(None) is None


class TestRowConversion:
    """Verify header row maps onto data rows correctly, ignoring unknown
    columns and blank rows."""

    def test_extracts_only_known_columns(self):
        header = ["Description", "Random", "Price", "Unit"]
        data = [["Ball Valve, 2\"", "ignore me", "$145.00", "EA"]]
        rows = _rows_with_headers(header, data)
        assert rows == [{
            "description": "Ball Valve, 2\"",
            "material_unit_cost": "$145.00",
            "unit": "EA",
        }]

    def test_skips_completely_blank_rows(self):
        header = ["Description", "Price"]
        data = [
            ["VAV-1", "500"],
            [None, None],
            ["", ""],
            ["VAV-2", "600"],
        ]
        rows = _rows_with_headers(header, data)
        assert len(rows) == 2

    def test_handles_missing_values(self):
        header = ["Description", "Model", "Price"]
        data = [["Item A", None, "100"]]
        rows = _rows_with_headers(header, data)
        assert "model_number" not in rows[0]
        assert rows[0]["description"] == "Item A"


class TestNormalize:
    """Final cleanup: parse numbers, default unit, apply default manufacturer."""

    def test_default_unit_is_ea(self):
        result = _normalize({"description": "Foo"}, None)
        assert result["unit"] == "EA"

    def test_default_category_uncategorized(self):
        result = _normalize({"description": "Foo"}, None)
        assert result["category"] == "uncategorized"

    def test_default_manufacturer_applied_when_missing(self):
        result = _normalize({"description": "Foo"}, default_manufacturer="Trane")
        assert result["manufacturer"] == "Trane"

    def test_default_manufacturer_does_not_overwrite(self):
        result = _normalize(
            {"description": "Foo", "manufacturer": "Carrier"},
            default_manufacturer="Trane",
        )
        assert result["manufacturer"] == "Carrier"

    def test_strips_whitespace(self):
        result = _normalize({"description": "  Pump  ", "manufacturer": " Bell "}, None)
        assert result["description"] == "Pump"
        assert result["manufacturer"] == "Bell"

    def test_money_string_converted(self):
        result = _normalize({"description": "Foo", "material_unit_cost": "$1,250.00"}, None)
        assert result["material_unit_cost"] == 1250.0


class TestParseBuffer:
    """End-to-end: feed a CSV byte buffer and verify parsed rows."""

    def test_parses_csv_with_realistic_headers(self):
        csv_content = (
            "CSI Code,Manufacturer,Model Number,Description,Size,UOM,List Price,Labor Hours\n"
            '23 73 13,Trane,CSAA012,"Air Handling Unit, 12,000 CFM",12000 CFM,EA,$31250.00,84\n'
            '23 73 13,Trane,CSAA020,"Air Handling Unit, 20,000 CFM",20000 CFM,EA,"$48,500",110\n'
        )
        rows = parse_buffer(csv_content.encode("utf-8"), "trane.csv")
        assert len(rows) == 2
        assert rows[0]["manufacturer"] == "Trane"
        assert rows[0]["model_number"] == "CSAA012"
        assert rows[0]["material_unit_cost"] == 31250.0
        assert rows[0]["unit"] == "EA"
        assert rows[1]["material_unit_cost"] == 48500.0

    def test_skips_rows_with_no_price(self):
        csv_content = (
            "Description,Price,Unit\n"
            "Boiler 1000 MBH,,EA\n"
            "Boiler 2000 MBH,$22500,EA\n"
        )
        rows = parse_buffer(csv_content.encode("utf-8"), "list.csv")
        # Both rows still come through; the loader decides what to do with
        # empties. Importer's job is only parsing.
        assert len(rows) == 2
        assert rows[0].get("material_unit_cost") is None
        assert rows[1]["material_unit_cost"] == 22500.0

    def test_unsupported_extension_raises(self):
        try:
            parse_buffer(b"foo", "list.txt")
        except ValueError as e:
            assert "Unsupported" in str(e)
        else:
            raise AssertionError("expected ValueError for .txt")
