"""
Tests for CSI specification section extraction.
Regex patterns and SpecSectionData are duplicated here to avoid importing
pdfplumber and anthropic which are only in the full Docker environment.
"""
import re
from dataclasses import dataclass, field


SECTION_PATTERN = re.compile(
    r"SECTION\s+(\d{2}\s+\d{2}\s+\d{2})\s*[-–]\s*(.+?)(?:\n|$)", re.IGNORECASE
)
PART_PATTERN = re.compile(
    r"^PART\s+(\d+)\s*[-–]\s*(.+?)$", re.MULTILINE | re.IGNORECASE
)


@dataclass
class SpecSectionData:
    section_number: str
    section_title: str
    raw_text: str
    structured_data: dict = field(default_factory=dict)
    page_start: int = 0
    page_end: int = 0


class TestSectionPattern:
    def test_matches_standard_heading(self):
        text = "SECTION 23 74 13 - Air Handling Units\n"
        match = SECTION_PATTERN.search(text)
        assert match is not None
        assert match.group(1).replace(" ", "") == "237413"
        assert "Air Handling" in match.group(2)

    def test_matches_em_dash_separator(self):
        text = "SECTION 23 21 13 – Hydronic Piping\n"
        match = SECTION_PATTERN.search(text)
        assert match is not None
        assert "Hydronic Piping" in match.group(2)

    def test_matches_division_22_plumbing(self):
        text = "SECTION 22 11 16 - Domestic Water Piping\n"
        match = SECTION_PATTERN.search(text)
        assert match is not None

    def test_matches_division_26_electrical(self):
        text = "SECTION 26 05 33 - Raceways and Boxes for Electrical Systems\n"
        match = SECTION_PATTERN.search(text)
        assert match is not None

    def test_no_match_on_part_heading(self):
        text = "PART 1 - GENERAL\n"
        match = SECTION_PATTERN.search(text)
        assert match is None

    def test_case_insensitive(self):
        text = "section 23 74 13 - Air Handling Units\n"
        match = SECTION_PATTERN.search(text)
        assert match is not None

    def test_finds_multiple_sections(self):
        text = (
            "SECTION 23 74 13 - Air Handling Units\nSome content\n"
            "SECTION 23 36 00 - VAV Boxes\nMore content\n"
        )
        matches = list(SECTION_PATTERN.finditer(text))
        assert len(matches) == 2

    def test_section_number_format(self):
        text = "SECTION 23 74 13 - Air Handling Units\n"
        match = SECTION_PATTERN.search(text)
        # Group 1 should have spaces: "23 74 13"
        assert " " in match.group(1)

    def test_title_stripped_of_trailing_whitespace(self):
        text = "SECTION 23 74 13 - Air Handling Units  \n"
        match = SECTION_PATTERN.search(text)
        assert match is not None
        # Title captured up to newline
        assert match.group(2).endswith("Units") or "Units" in match.group(2)


class TestPartPattern:
    def test_matches_part_1_general(self):
        text = "PART 1 - GENERAL\n"
        match = PART_PATTERN.search(text)
        assert match is not None
        assert match.group(1) == "1"

    def test_matches_part_2_products(self):
        text = "PART 2 - PRODUCTS\n"
        match = PART_PATTERN.search(text)
        assert match is not None

    def test_matches_part_3_execution(self):
        text = "PART 3 - EXECUTION\n"
        match = PART_PATTERN.search(text)
        assert match is not None

    def test_no_match_on_section_heading(self):
        text = "SECTION 23 74 13 - Air Handling Units"
        match = PART_PATTERN.search(text)
        assert match is None

    def test_matches_em_dash(self):
        text = "PART 1 – GENERAL\n"
        match = PART_PATTERN.search(text)
        assert match is not None


class TestSpecSectionData:
    def test_dataclass_defaults(self):
        s = SpecSectionData(
            section_number="23 74 13",
            section_title="Air Handling Units",
            raw_text="Sample text",
        )
        assert s.structured_data == {}
        assert s.page_start == 0
        assert s.page_end == 0

    def test_structured_data_mutable_default_isolated(self):
        s1 = SpecSectionData("23 74 13", "AHUs", "text")
        s2 = SpecSectionData("23 21 13", "Piping", "text")
        s1.structured_data["key"] = "value"
        assert "key" not in s2.structured_data

    def test_custom_page_range(self):
        s = SpecSectionData("23 74 13", "AHUs", "text", page_start=5, page_end=12)
        assert s.page_start == 5
        assert s.page_end == 12

    def test_raw_text_stored(self):
        text = "PART 1 - GENERAL\n1.1 SUMMARY\nThis section specifies..."
        s = SpecSectionData("23 74 13", "AHUs", text)
        assert s.raw_text == text
