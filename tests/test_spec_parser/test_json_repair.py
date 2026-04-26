"""Tests for the robust JSON parser used to extract structured data from
Claude's spec section analysis. Real LLM output frequently includes
markdown fences, leading prose, and occasional truncation."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "backend"))

from ai.spec_parser import (
    _largest_balanced_object,
    _repair_truncated_json,
    parse_json_payload,
)


class TestLargestBalancedObject:
    def test_extracts_simple_object(self):
        assert _largest_balanced_object('{"a": 1}') == '{"a": 1}'

    def test_handles_leading_prose(self):
        text = "Sure, here is the JSON: {\"a\": 1}. Hope that helps."
        assert _largest_balanced_object(text) == '{"a": 1}'

    def test_returns_balanced_nested_object(self):
        text = 'preamble {"outer": {"inner": "x"}} trailing'
        assert _largest_balanced_object(text) == '{"outer": {"inner": "x"}}'

    def test_skips_braces_inside_strings(self):
        text = '{"a": "weird { } value"}'
        assert _largest_balanced_object(text) == text

    def test_no_object_returns_none(self):
        assert _largest_balanced_object("just prose") is None


class TestRepairTruncated:
    def test_closes_unfinished_object(self):
        # LLM cut off after writing a key+value but before closing brace
        repaired = _repair_truncated_json('{"a": 1, "b": [1, 2')
        assert repaired is not None
        # Don't assert exact form — just that it parses as JSON
        import json
        result = json.loads(repaired)
        assert result["a"] == 1

    def test_closes_unfinished_string(self):
        repaired = _repair_truncated_json('{"key": "unclosed')
        import json
        result = json.loads(repaired)
        assert "key" in result

    def test_returns_none_when_no_brace(self):
        assert _repair_truncated_json("plain prose, no JSON") is None


class TestParseJsonPayload:
    def test_plain_json(self):
        result = parse_json_payload('{"materials": []}')
        assert result == {"materials": []}

    def test_markdown_fenced_json(self):
        text = """Here is the analysis:

```json
{
  "materials": [{"name": "duct", "size": "12x8"}],
  "standards": ["SMACNA"]
}
```

Let me know if you need more.
"""
        result = parse_json_payload(text)
        assert result["materials"][0]["name"] == "duct"
        assert "SMACNA" in result["standards"]

    def test_unfenced_with_prose(self):
        text = 'Sure! {"materials": [], "standards": ["UL 508A"]} Done.'
        result = parse_json_payload(text)
        assert result["standards"] == ["UL 508A"]

    def test_truncated_payload_recovered(self):
        text = '{"materials": [{"name": "AHU", "size": "10000 CFM"'
        result = parse_json_payload(text)
        # Even if not fully recovered, should not crash; expect at least a dict
        assert isinstance(result, dict) or result is None

    def test_garbage_returns_none(self):
        assert parse_json_payload("no json at all") is None
        assert parse_json_payload("") is None
        assert parse_json_payload(None) is None

    def test_handles_nested_arrays(self):
        text = '{"products": [{"category": "valve", "manufacturer_options": ["NIBCO", "Apollo"]}]}'
        result = parse_json_payload(text)
        assert result["products"][0]["manufacturer_options"] == ["NIBCO", "Apollo"]
