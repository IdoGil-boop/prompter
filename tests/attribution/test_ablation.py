"""Tests for AblationSweep — component ablation attribution."""
from __future__ import annotations

import pytest

from prompter.attribution.ablation import AblationResult, AblationSweep
from prompter.config.agent_config import AgentConfig, ToolSpec
from prompter.eval.evaluator import EvalReport, Evaluator, TestResult
from prompter.eval.test_suite import TestCase, TestSuite
from tests.conftest import MockLLM


class TestAblationResult:
    def test_frozen_dataclass(self) -> None:
        result = AblationResult(
            component_deltas={"system_prompt": 0.5},
            baseline_score=0.8,
        )
        assert result.component_deltas == {"system_prompt": 0.5}
        assert result.baseline_score == 0.8

    def test_immutable(self) -> None:
        result = AblationResult(component_deltas={}, baseline_score=0.5)
        try:
            result.baseline_score = 1.0  # type: ignore[misc]
            assert False, "Should be frozen"
        except AttributeError:
            pass


class TestAblationSweep:
    @pytest.mark.asyncio
    async def test_ablation_identifies_helpful_component(self) -> None:
        """Removing a helpful tool drops score => positive delta."""
        config = AgentConfig(
            system_prompt="Be helpful",
            tools={
                "calc": ToolSpec(
                    name="calc",
                    description="Calculator",
                    parameters_schema={},
                    implementation="def calc(x): return str(eval(x))",
                ),
            },
        )
        suite = TestSuite(
            tests=[
                TestCase(id="t1", input="hi", expected="hello", eval_mode="exact_match"),
            ],
        )

        # component_names() order: ["system_prompt", "tool:calc"]
        # Scores: baseline=0.8, without system_prompt=0.5, without calc=0.3
        call_count = 0
        scores = [0.8, 0.5, 0.3]  # baseline, -system_prompt, -calc

        class FakeEvaluator:
            async def evaluate(self, agent_fn, test_suite, config_id=""):
                nonlocal call_count
                score = scores[call_count]
                call_count += 1
                return EvalReport(
                    config_id=config_id,
                    aggregate_score=score,
                    results=[TestResult(test_id="t1", score=score, actual_output="x")],
                )

        llm = MockLLM(responses=lambda msgs: "hello")
        sweep = AblationSweep()
        result = await sweep.run(config, suite, FakeEvaluator(), llm)  # type: ignore[arg-type]

        assert result.baseline_score == 0.8
        # calc is helpful: removing it drops score 0.8->0.3 => delta=0.5
        assert result.component_deltas["tool:calc"] == pytest.approx(0.5)
        # system_prompt: removing drops 0.8->0.5 => delta=0.3
        assert result.component_deltas["system_prompt"] == pytest.approx(0.3)

    @pytest.mark.asyncio
    async def test_ablation_identifies_harmful_component(self) -> None:
        """Removing a harmful tool improves score => negative delta."""
        config = AgentConfig(
            system_prompt="Be helpful",
            tools={
                "bad_tool": ToolSpec(
                    name="bad_tool",
                    description="Confusing tool",
                    parameters_schema={},
                    implementation="def bad(): return 'noise'",
                ),
            },
        )
        suite = TestSuite(
            tests=[
                TestCase(id="t1", input="hi", expected="hello", eval_mode="exact_match"),
            ],
        )

        # component_names() order: ["system_prompt", "tool:bad_tool"]
        call_count = 0
        scores = [0.4, 0.3, 0.7]  # baseline, -system_prompt, -bad_tool

        class FakeEvaluator:
            async def evaluate(self, agent_fn, test_suite, config_id=""):
                nonlocal call_count
                score = scores[call_count]
                call_count += 1
                return EvalReport(
                    config_id=config_id,
                    aggregate_score=score,
                    results=[TestResult(test_id="t1", score=score, actual_output="x")],
                )

        llm = MockLLM(responses=lambda msgs: "hello")
        sweep = AblationSweep()
        result = await sweep.run(config, suite, FakeEvaluator(), llm)  # type: ignore[arg-type]

        assert result.baseline_score == 0.4
        # Removing bad_tool IMPROVES score: 0.4->0.7 => delta = -0.3 (negative = hurts)
        assert result.component_deltas["tool:bad_tool"] == pytest.approx(-0.3)

    @pytest.mark.asyncio
    async def test_ablation_no_tools(self) -> None:
        """Config with only system_prompt: still ablates system_prompt."""
        config = AgentConfig(system_prompt="Be helpful")
        suite = TestSuite(
            tests=[TestCase(id="t1", input="hi", expected="hello", eval_mode="exact_match")],
        )

        call_count = 0
        scores = [0.8, 0.2]  # baseline, -system_prompt

        class FakeEvaluator:
            async def evaluate(self, agent_fn, test_suite, config_id=""):
                nonlocal call_count
                score = scores[call_count]
                call_count += 1
                return EvalReport(
                    config_id=config_id,
                    aggregate_score=score,
                    results=[TestResult(test_id="t1", score=score, actual_output="x")],
                )

        llm = MockLLM(responses=lambda msgs: "hello")
        sweep = AblationSweep()
        result = await sweep.run(config, suite, FakeEvaluator(), llm)  # type: ignore[arg-type]

        assert result.baseline_score == 0.8
        assert "system_prompt" in result.component_deltas
        assert result.component_deltas["system_prompt"] == pytest.approx(0.6)
