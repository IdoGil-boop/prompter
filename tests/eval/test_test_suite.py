"""Tests for TestSuite — YAML loading, filtering, weights."""
from __future__ import annotations

import tempfile
from pathlib import Path

import pytest

from prompter.eval.test_suite import TestCase, TestSuite


class TestTestSuite:
    def test_load_from_yaml(self) -> None:
        yaml_content = """
tests:
  - id: t1
    input: "hello"
    expected: "world"
    eval: exact_match
  - id: t2
    input: "foo"
    expected: "bar"
    eval: exact_match
"""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            f.write(yaml_content)
            path = Path(f.name)

        suite = TestSuite.load(path)
        path.unlink()

        assert len(suite.tests) == 2
        assert suite.tests[0].id == "t1"
        assert suite.tests[0].input == "hello"
        assert suite.tests[0].expected == "world"

    def test_save_and_load_round_trip(self) -> None:
        suite = TestSuite(tests=[
            TestCase(id="t1", input="a", expected="b", eval_mode="exact_match"),
        ])
        with tempfile.NamedTemporaryFile(suffix=".yaml", delete=False) as f:
            path = Path(f.name)

        suite.save(path)
        loaded = TestSuite.load(path)
        path.unlink()

        assert len(loaded.tests) == 1
        assert loaded.tests[0].id == "t1"

    def test_filter_by_tags(self) -> None:
        suite = TestSuite(tests=[
            TestCase(id="t1", input="a", expected="b", eval_mode="exact_match", tags=["fast"]),
            TestCase(id="t2", input="c", expected="d", eval_mode="exact_match", tags=["slow"]),
            TestCase(
                id="t3", input="e", expected="f",
                eval_mode="exact_match", tags=["fast", "slow"],
            ),
        ])
        fast_suite = suite.filter_by_tags(["fast"])
        assert len(fast_suite.tests) == 2
        assert {t.id for t in fast_suite.tests} == {"t1", "t3"}

    def test_total_weight(self) -> None:
        suite = TestSuite(tests=[
            TestCase(id="t1", input="a", expected="b", eval_mode="exact_match", weight=2.0),
            TestCase(id="t2", input="c", expected="d", eval_mode="exact_match", weight=3.0),
        ])
        assert suite.total_weight == 5.0

    def test_load_invalid_yaml_raises(self) -> None:
        yaml_content = "not_tests: []"
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            f.write(yaml_content)
            path = Path(f.name)

        with pytest.raises(ValueError, match="tests"):
            TestSuite.load(path)
        path.unlink()

    def test_metadata_preserved(self) -> None:
        yaml_content = """
name: "My test suite"
version: "1.0"
tests:
  - id: t1
    input: "a"
    expected: "b"
    eval: exact_match
"""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            f.write(yaml_content)
            path = Path(f.name)

        suite = TestSuite.load(path)
        path.unlink()

        assert suite.metadata.get("name") == "My test suite"


class TestTestCase:
    def test_from_dict_defaults(self) -> None:
        tc = TestCase.from_dict({"id": "t1", "input": "a", "expected": "b"})
        assert tc.eval_mode == "exact_match"
        assert tc.weight == 1.0
        assert tc.tags == []
        assert tc.context is None

    def test_to_dict_round_trip(self) -> None:
        tc = TestCase(
            id="t1", input="a", expected="b", eval_mode="exact_match",
            weight=2.0, tags=["fast"],
        )
        d = tc.to_dict()
        loaded = TestCase.from_dict(d)
        assert loaded.id == tc.id
        assert loaded.weight == tc.weight
        assert loaded.tags == tc.tags
