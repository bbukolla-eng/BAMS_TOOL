"""Equipment metadata extraction — pull structured data from DXF block
attributes and nearby annotation text."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "backend"))

from ai.div23.equipment_metadata import (
    _normalize_attribs,
    extract_metadata,
    extract_tag,
    parse_capacity,
    parse_size_token,
    text_within_radius,
)


class TestSizeToken:
    def test_rectangular_xX_separator(self):
        assert parse_size_token("12x12") == "12x12"
        assert parse_size_token("24X24") == "24x24"
        assert parse_size_token(" 36 X 18 ") == "36x18"

    def test_diameter_inch_quote(self):
        assert parse_size_token("10\"") == "10\""

    def test_diameter_inch_word(self):
        assert parse_size_token("8 inch") == "8\""
        assert parse_size_token("12 IN") == "12\""

    def test_returns_none_for_no_size(self):
        assert parse_size_token("AHU-1") is None
        assert parse_size_token(None) is None
        assert parse_size_token("") is None


class TestCapacity:
    def test_extracts_cfm(self):
        assert parse_capacity("10,000 CFM").get("cfm") == 10000.0
        assert parse_capacity("AHU-1 / 12000 CFM / 480V").get("cfm") == 12000.0

    def test_extracts_tons(self):
        assert parse_capacity("CHILLER-1 50 ton").get("tons") == 50.0

    def test_extracts_mbh(self):
        assert parse_capacity("BLR-1 1000 MBH").get("mbh") == 1000.0

    def test_extracts_gpm(self):
        assert parse_capacity("PUMP-1 200 GPM").get("gpm") == 200.0

    def test_extracts_hp(self):
        assert parse_capacity("EF-1 5 HP 480V").get("hp") == 5.0

    def test_extracts_voltage(self):
        assert parse_capacity("480V").get("voltage") == 480

    def test_empty_input_returns_empty_dict(self):
        assert parse_capacity("") == {}
        assert parse_capacity(None) == {}


class TestTagExtraction:
    def test_pulls_ahu_tag(self):
        assert extract_tag("AHU-1 12,000 CFM") == "AHU-1"

    def test_pulls_decimal_tag(self):
        assert extract_tag("VAV-3.2") == "VAV-3.2"

    def test_skips_size_only(self):
        # "12x12" should NOT be treated as a tag
        assert extract_tag("12x12") is None

    def test_finds_tag_alongside_size(self):
        assert extract_tag("FCU-04 12x12") == "FCU-04"


class TestAttribNormalization:
    def test_aliased_keys_canonicalize(self):
        result = _normalize_attribs({"MARK": "AHU-1", "MFR": "Trane", "AIRFLOW": "12000"})
        assert result["tag"] == "AHU-1"
        assert result["manufacturer"] == "Trane"
        assert result["cfm"] == 12000.0

    def test_size_attrib_normalized(self):
        result = _normalize_attribs({"SIZE": "24X24"})
        assert result["size"] == "24x24"

    def test_inlet_attrib_normalized(self):
        result = _normalize_attribs({"INLET": "8\""})
        assert result["inlet_size"] == "8\""

    def test_voltage_coerced_to_int(self):
        result = _normalize_attribs({"VOLTS": "480"})
        assert result["voltage"] == 480

    def test_unknown_keys_dropped(self):
        result = _normalize_attribs({"RANDOM_FIELD": "ignore"})
        assert "RANDOM_FIELD" not in result


class TestExtractMetadata:
    def test_block_attribs_win_over_text(self):
        block = {"name": "AHU", "attribs": {"TAG": "AHU-1"}}
        # Even with conflicting text, the attribute is preferred
        result = extract_metadata(block, nearby_text=["AHU-99"])
        assert result["tag"] == "AHU-1"

    def test_text_fills_gaps_when_attribs_missing(self):
        block = {"name": "AHU", "attribs": {}}
        result = extract_metadata(block, nearby_text=["AHU-1 / 10,000 CFM"])
        assert result["tag"] == "AHU-1"
        assert result["cfm"] == 10000.0

    def test_no_metadata_returns_empty(self):
        result = extract_metadata({"name": "AHU"}, nearby_text=[])
        assert result == {}


class TestProximityText:
    def test_finds_text_within_radius_sorted(self):
        elements = [
            {"x": 1.0, "y": 1.0, "text": "near"},
            {"x": 0.5, "y": 0.5, "text": "nearer"},
            {"x": 100.0, "y": 100.0, "text": "far"},
        ]
        found = text_within_radius(0.0, 0.0, elements, radius_ft=5.0)
        assert "nearer" in found
        assert "near" in found
        assert "far" not in found
        # Sorted nearest-first
        assert found.index("nearer") < found.index("near")

    def test_skips_blank_text(self):
        elements = [{"x": 0, "y": 0, "text": "   "}, {"x": 0, "y": 0, "text": "good"}]
        found = text_within_radius(0, 0, elements, radius_ft=2.0)
        assert found == ["good"]
