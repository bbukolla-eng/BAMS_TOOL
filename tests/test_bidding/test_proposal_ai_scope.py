"""Tests for the Claude-driven proposal scope generator. We exercise the
deterministic fallback (no Claude key) and the structural shape of the
prompt + response coercion."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "backend"))

from modules.proposals.ai_scope import (
    _build_prompt,
    _category_summary,
    _coerce_scope_dict,
    _deterministic_fallback,
    _summarize_specs,
    _summarize_takeoff,
)


class _FakeItem:
    def __init__(self, category, description, quantity=10, unit="LF",
                 csi_code="23 31 13", adjusted_quantity=None):
        self.category = category
        self.description = description
        self.quantity = quantity
        self.adjusted_quantity = adjusted_quantity if adjusted_quantity is not None else quantity * 1.05
        self.unit = unit
        self.csi_code = csi_code


class _FakeSection:
    def __init__(self, number, title):
        self.section_number = number
        self.section_title = title


class TestSummarizeTakeoff:
    def test_basic_lines(self):
        items = [
            _FakeItem("duct_rectangular", "12x8 supply duct", quantity=100, unit="LF"),
            _FakeItem("ahu", "AHU-1", quantity=1, unit="EA"),
        ]
        lines = _summarize_takeoff(items)
        assert len(lines) == 2
        assert "12x8 supply duct" in lines[0]
        assert "AHU-1" in lines[1]

    def test_truncates_with_overflow_marker(self):
        items = [_FakeItem("duct", f"item {i}") for i in range(80)]
        lines = _summarize_takeoff(items, limit=10)
        assert len(lines) == 11
        assert "70 additional" in lines[-1]

    def test_uses_adjusted_quantity_when_present(self):
        item = _FakeItem("duct", "supply", quantity=100, adjusted_quantity=105)
        lines = _summarize_takeoff([item])
        assert "105.0" in lines[0]


class TestSummarizeSpecs:
    def test_includes_section_number(self):
        sections = [
            _FakeSection("23 31 13", "Metal Ducts"),
            _FakeSection("23 73 13", "Modular AHUs"),
        ]
        lines = _summarize_specs(sections)
        assert any("23 31 13" in line for line in lines)
        assert any("Metal Ducts" in line for line in lines)


class TestCategorySummary:
    def test_aggregates_counts(self):
        items = [
            _FakeItem("duct_rectangular", "a"),
            _FakeItem("duct_rectangular", "b"),
            _FakeItem("ahu", "c"),
        ]
        result = _category_summary(items)
        assert result == {"duct_rectangular": 2, "ahu": 1}


class TestDeterministicFallback:
    def test_includes_ductwork_when_present(self):
        ctx = {"takeoff_categories": {"duct_rectangular": 5, "duct_round": 2}}
        result = _deterministic_fallback(ctx)
        assert "Ductwork" in result["scope_of_work"]

    def test_omits_ductwork_when_absent(self):
        ctx = {"takeoff_categories": {"ahu": 1}}
        result = _deterministic_fallback(ctx)
        assert "Ductwork" not in result["scope_of_work"]
        assert "Equipment" in result["scope_of_work"]

    def test_includes_pipe_when_present(self):
        ctx = {"takeoff_categories": {"pipe_steel": 5}}
        result = _deterministic_fallback(ctx)
        assert "piping" in result["scope_of_work"].lower()

    def test_exclusions_mention_power_wiring(self):
        ctx = {"takeoff_categories": {}}
        result = _deterministic_fallback(ctx)
        assert "Power wiring" in result["exclusions"]
        assert "Controls programming" in result["exclusions"]

    def test_all_four_keys_returned(self):
        ctx = {"takeoff_categories": {}}
        result = _deterministic_fallback(ctx)
        assert {"scope_of_work", "inclusions", "exclusions", "clarifications"} <= set(result.keys())


class TestPromptAssembly:
    def test_includes_takeoff_block(self):
        ctx = {
            "project_name": "Test Project",
            "project_address": "100 Main St",
            "takeoff_lines": ["- 100.0 LF — supply duct"],
            "spec_lines": ["- 23 31 13 — Metal Ducts"],
            "has_division_23_specs": True,
        }
        prompt = _build_prompt(ctx)
        assert "100.0 LF" in prompt
        assert "23 31 13" in prompt
        assert "Test Project" in prompt
        assert "100 Main St" in prompt
        assert "JSON" in prompt

    def test_handles_empty_blocks(self):
        ctx = {
            "project_name": "Empty Project",
            "project_address": None,
            "takeoff_lines": [],
            "spec_lines": [],
            "has_division_23_specs": False,
        }
        prompt = _build_prompt(ctx)
        assert "(no takeoff items)" in prompt
        assert "(no spec sections)" in prompt


class TestCoerceScopeDict:
    def test_string_values_used_directly(self):
        ctx = {"takeoff_categories": {}}
        parsed = {
            "scope_of_work": "Custom scope text",
            "inclusions": "Custom inclusions",
        }
        result = _coerce_scope_dict(parsed, ctx)
        assert result["scope_of_work"] == "Custom scope text"
        assert result["inclusions"] == "Custom inclusions"
        # Missing fields fall back to deterministic skeleton
        assert "Power wiring" in result["exclusions"]

    def test_list_values_become_bullet_lines(self):
        ctx = {"takeoff_categories": {}}
        parsed = {"inclusions": ["Materials", "Labor", "TAB"]}
        result = _coerce_scope_dict(parsed, ctx)
        assert "- Materials" in result["inclusions"]
        assert "- Labor" in result["inclusions"]
        assert "- TAB" in result["inclusions"]

    def test_blank_string_falls_back(self):
        ctx = {"takeoff_categories": {}}
        parsed = {"scope_of_work": "   "}
        result = _coerce_scope_dict(parsed, ctx)
        assert result["scope_of_work"] != "   "
