"""Tests for Evaluator — full eval with mock agent_fn."""
from __future__ import annotations

import pytest

from prompter.eval.evaluator import EvalReport, Evaluator
from prompter.eval.test_suite import TestCase, TestSuite


class TestEvaluator:
    async def test_perfect_score(self) -> None:
        """Agent that returns exact matches should score 1.0."""
        async def agent_fn(input_text: str, context: dict | None = None) -> str:
            if "hello" in input_text.lower():
                return "hello"
            return "goodbye"

        suite = TestSuite(tests=[
            TestCase(id="t1", input="Say hello", expected="hello", eval_mode="exact_match"),
            TestCase(id="t2", input="Say goodbye", expected="goodbye", eval_mode="exact_match"),
        ])
        evaluator = Evaluator(n_runs=1)
        report = await evaluator.evaluate(agent_fn, suite, "test-config")

        assert report.aggregate_score == 1.0
        assert len(report.passed) == 2
        assert len(report.failed) == 0

    async def test_zero_score(self) -> None:
        """Agent that returns wrong outputs should score 0.0."""
        async def agent_fn(input_text: str, context: dict | None = None) -> str:
            return "wrong answer"

        suite = TestSuite(tests=[
            TestCase(id="t1", input="Say hello", expected="hello", eval_mode="exact_match"),
        ])
        evaluator = Evaluator(n_runs=1)
        report = await evaluator.evaluate(agent_fn, suite, "test")

        assert report.aggregate_score == 0.0
        assert len(report.failed) == 1

    async def test_partial_score(self) -> None:
        """Agent that gets some right should have partial score."""
        async def agent_fn(input_text: str, context: dict | None = None) -> str:
            if "hello" in input_text:
                return "hello"
            return "wrong"

        suite = TestSuite(tests=[
            TestCase(id="t1", input="Say hello", expected="hello", eval_mode="exact_match"),
            TestCase(id="t2", input="Say bye", expected="bye", eval_mode="exact_match"),
        ])
        evaluator = Evaluator(n_runs=1)
        report = await evaluator.evaluate(agent_fn, suite, "test")

        assert report.aggregate_score == 0.5
        assert len(report.passed) == 1
        assert len(report.failed) == 1

    async def test_agent_error_scores_zero(self) -> None:
        """Agent that raises should get score 0 for that test."""
        async def agent_fn(input_text: str, context: dict | None = None) -> str:
            raise ValueError("Agent crashed")

        suite = TestSuite(tests=[
            TestCase(id="t1", input="hi", expected="hi", eval_mode="exact_match"),
        ])
        evaluator = Evaluator(n_runs=1)
        report = await evaluator.evaluate(agent_fn, suite, "test")

        assert report.aggregate_score == 0.0
        assert report.results[0].error is not None

    async def test_weighted_scoring(self) -> None:
        """Weights should affect aggregate score."""
        async def agent_fn(input_text: str, context: dict | None = None) -> str:
            if "important" in input_text:
                return "correct"
            return "wrong"

        suite = TestSuite(tests=[
            TestCase(
                id="t1", input="important", expected="correct",
                eval_mode="exact_match", weight=3.0,
            ),
            TestCase(
                id="t2", input="trivial", expected="correct",
                eval_mode="exact_match", weight=1.0,
            ),
        ])
        evaluator = Evaluator(n_runs=1)
        report = await evaluator.evaluate(agent_fn, suite, "test")

        # t1 passes (weight 3), t2 fails (weight 1), aggregate = 3/4 = 0.75
        assert report.aggregate_score == pytest.approx(0.75)

    async def test_pass_rate_property(self) -> None:
        async def agent_fn(input_text: str, context: dict | None = None) -> str:
            return "hello"

        suite = TestSuite(tests=[
            TestCase(id="t1", input="hi", expected="hello", eval_mode="exact_match"),
            TestCase(id="t2", input="hi", expected="world", eval_mode="exact_match"),
        ])
        evaluator = Evaluator(n_runs=1)
        report = await evaluator.evaluate(agent_fn, suite, "test")

        assert report.pass_rate == 0.5

    async def test_empty_report_pass_rate(self) -> None:
        report = EvalReport(config_id="test", aggregate_score=0.0, results=[])
        assert report.pass_rate == 0.0
