"""Cosine-similarity linking math + symbol/run description rendering."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "backend"))

from ai.spec_drawing_linker import (
    _coerce_embedding,
    _section_relevant_to_division,
    _top_matches,
    cosine_similarity,
    describe_run,
    describe_symbol,
)


class TestCosineSimilarity:
    def test_identical_vectors_score_one(self):
        v = [0.1, 0.2, 0.3]
        assert abs(cosine_similarity(v, v) - 1.0) < 1e-9

    def test_orthogonal_vectors_score_zero(self):
        assert abs(cosine_similarity([1, 0], [0, 1])) < 1e-9

    def test_opposite_vectors_score_negative_one(self):
        assert abs(cosine_similarity([1, 0], [-1, 0]) + 1.0) < 1e-9

    def test_empty_returns_zero(self):
        assert cosine_similarity([], [1, 2]) == 0.0
        assert cosine_similarity([1, 2], []) == 0.0

    def test_zero_vector_returns_zero(self):
        assert cosine_similarity([0, 0], [1, 2]) == 0.0

    def test_mismatched_lengths_returns_zero(self):
        assert cosine_similarity([1, 2, 3], [1, 2]) == 0.0


class TestSymbolDescription:
    def test_basic_symbol_type_only(self):
        assert describe_symbol("ahu", None) == "ahu"
        assert describe_symbol("vav_box", {}) == "vav box"

    def test_includes_size_capacity_model(self):
        text = describe_symbol("ahu", {
            "size": "12000 CFM",
            "tons": 30,
            "model": "CSAA012",
            "manufacturer": "Trane",
        })
        assert "ahu" in text
        assert "size 12000 CFM" in text
        assert "30 ton" in text
        assert "CSAA012" in text
        assert "Trane" in text

    def test_inlet_size_for_vav(self):
        text = describe_symbol("vav_box", {"inlet_size": "8\""})
        assert "inlet 8\"" in text


class TestRunDescription:
    def test_with_size(self):
        assert describe_run("duct_supply", "12x8") == "duct supply, 12x8"

    def test_no_size(self):
        assert describe_run("pipe_chw", None) == "pipe chw"


class TestDivisionRelevance:
    def test_section_in_div_23(self):
        assert _section_relevant_to_division("23 31 13", "23")

    def test_section_in_other_division_skipped(self):
        assert not _section_relevant_to_division("26 05 00", "23")

    def test_blank_section_relevant_by_default(self):
        # If we don't know the section number, don't filter aggressively
        assert _section_relevant_to_division(None, "23")
        assert _section_relevant_to_division("", "23")


class TestEmbeddingCoercion:
    def test_list_passes_through(self):
        assert _coerce_embedding([0.1, 0.2]) == [0.1, 0.2]

    def test_string_with_brackets_parsed(self):
        assert _coerce_embedding("[0.1, 0.2, 0.3]") == [0.1, 0.2, 0.3]

    def test_string_no_brackets_parsed(self):
        assert _coerce_embedding("0.1, 0.2") == [0.1, 0.2]

    def test_none_returns_none(self):
        assert _coerce_embedding(None) is None

    def test_empty_string_returns_none(self):
        assert _coerce_embedding("") is None
        assert _coerce_embedding("[]") is None


class TestTopMatches:
    def test_filters_below_threshold(self):
        # vector v matches section_a perfectly, has 0 similarity with b
        v = [1, 0]

        class _Section:
            def __init__(self, sid):
                self.id = sid

        sections = [(_Section(1), [1, 0]), (_Section(2), [0, 1])]
        matches = _top_matches(v, sections, threshold=0.5)
        assert len(matches) == 1
        assert matches[0][0].id == 1

    def test_returns_at_most_top_n(self):
        from ai.spec_drawing_linker import TOP_MATCHES_PER_ITEM

        class _Section:
            def __init__(self, sid):
                self.id = sid

        v = [1, 0]
        # 5 sections, all perfectly matching
        sections = [(_Section(i), [1, 0]) for i in range(5)]
        matches = _top_matches(v, sections, threshold=0.5)
        assert len(matches) == TOP_MATCHES_PER_ITEM

    def test_sorted_descending(self):
        class _Section:
            def __init__(self, sid):
                self.id = sid

        v = [1, 0]
        sections = [
            (_Section(1), [0.5, 0.5]),  # ~0.707
            (_Section(2), [1, 0]),       # 1.0
            (_Section(3), [0.7, 0.3]),  # ~0.92
        ]
        matches = _top_matches(v, sections, threshold=0.5)
        assert matches[0][0].id == 2
        assert matches[1][0].id == 3
        assert matches[2][0].id == 1
