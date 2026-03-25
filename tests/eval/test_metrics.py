"""Tests for metric functions — exact_match, contains, semantic_similarity, etc."""
from __future__ import annotations

import pytest

from prompter.eval.metrics import (
    contains_match,
    exact_match,
    score_output,
    tool_call_match,
)


class TestExactMatch:
    def test_exact_match_identical(self) -> None:
        assert exact_match("hello", "hello") == 1.0

    def test_exact_match_different(self) -> None:
        assert exact_match("hello", "world") == 0.0

    def test_exact_match_case_insensitive(self) -> None:
        assert exact_match("Hello", "hello", {"case_insensitive": True}) == 1.0

    def test_exact_match_strips_whitespace_by_default(self) -> None:
        assert exact_match("  hello  ", "hello") == 1.0

    def test_exact_match_normalize_whitespace(self) -> None:
        assert exact_match("hello  world", "hello world", {"normalize_whitespace": True}) == 1.0

    def test_exact_match_empty_strings(self) -> None:
        assert exact_match("", "") == 1.0

    def test_exact_match_one_empty(self) -> None:
        assert exact_match("", "hello") == 0.0


class TestContainsMatch:
    def test_contains_present(self) -> None:
        assert contains_match("hello world", "hello") == 1.0

    def test_contains_absent(self) -> None:
        assert contains_match("hello world", "xyz") == 0.0

    def test_contains_case_insensitive_default(self) -> None:
        assert contains_match("Hello World", "hello") == 1.0


class TestToolCallMatch:
    def test_matching_tool_name(self) -> None:
        actual = {"tool_name": "search", "args": {"q": "test"}}
        expected = {"tool_name": "search", "args": {"q": "test"}}
        assert tool_call_match(actual, expected) == 1.0

    def test_different_tool_name(self) -> None:
        actual = {"tool_name": "search", "args": {}}
        expected = {"tool_name": "calculate", "args": {}}
        assert tool_call_match(actual, expected) == 0.0

    def test_partial_arg_match(self) -> None:
        actual = {"tool_name": "search", "args": {"q": "test", "limit": 10}}
        expected = {"tool_name": "search", "args": {"q": "test", "limit": 5}}
        score = tool_call_match(actual, expected)
        assert 0.0 < score < 1.0  # Partial match

    def test_no_args_check(self) -> None:
        actual = {"tool_name": "search", "args": {"q": "wrong"}}
        expected = {"tool_name": "search", "args": {"q": "right"}}
        assert tool_call_match(actual, expected, {"check_args": False}) == 1.0

    def test_invalid_input_returns_zero(self) -> None:
        assert tool_call_match("not json", "also not json") == 0.0


class TestScoreOutput:
    def test_dispatches_to_exact_match(self) -> None:
        assert score_output("hello", "hello", "exact_match") == 1.0

    def test_unknown_mode_raises(self) -> None:
        with pytest.raises(ValueError, match="Unknown eval mode"):
            score_output("a", "b", "nonexistent_mode")
