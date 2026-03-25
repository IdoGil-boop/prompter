"""Tests for variance modes in the optimizer."""
from __future__ import annotations

import json
import tempfile
from pathlib import Path

import pytest

from prompter.config.agent_config import AgentConfig
from prompter.eval.evaluator import Evaluator
from prompter.eval.test_suite import TestCase, TestSuite
from prompter.eval.variance import VarianceTracker, effective_score
from prompter.llm.adapter import LLMResponse, Message, TokenUsage
from prompter.optimizer import Optimizer, OptimizerConfig
from tests.conftest import MockLLM


class TestVarianceModes:
    """Tests for variance_modes in OptimizerConfig."""

    def test_optimizer_config_has_variance_modes(self) -> None:
        """OptimizerConfig should have variance_modes field."""
        config = OptimizerConfig(variance_modes=["run", "order"])
        assert config.variance_modes == ["run", "order"]

    def test_optimizer_config_default_variance_modes(self) -> None:
        """Default variance_modes should be ['run']."""
        config = OptimizerConfig()
        assert config.variance_modes == ["run"]

    def test_invalid_variance_mode_raises(self) -> None:
        """Invalid variance modes should raise ValueError."""
        with pytest.raises(ValueError, match="Invalid variance mode"):
            OptimizerConfig(variance_modes=["run", "invalid_mode"])


class TestOrderVariance:
    """Tests for order variance computation."""

    def test_variance_tracker_order_variant(self) -> None:
        """VarianceTracker should track order variant scores."""
        tracker = VarianceTracker()
        tracker.add_run([0.8, 0.9, 0.7])
        tracker.add_order_variant(0.85)
        tracker.add_order_variant(0.75)
        report = tracker.report()
        assert report.order_variance is not None
        assert report.order_variance > 0

    def test_order_variance_in_total(self) -> None:
        """Order variance should contribute to total_variance."""
        tracker = VarianceTracker()
        tracker.add_run([0.8, 0.9])
        tracker.add_run([0.85, 0.85])
        tracker.add_order_variant(0.8)
        tracker.add_order_variant(0.9)
        report = tracker.report()
        assert report.total_variance > 0


class TestParaphraseVariance:
    """Tests for paraphrase variance."""

    def test_variance_tracker_paraphrase(self) -> None:
        """VarianceTracker should track paraphrase variant scores."""
        tracker = VarianceTracker()
        tracker.add_run([0.8, 0.9, 0.7])
        tracker.add_paraphrase_variant(0.85)
        tracker.add_paraphrase_variant(0.75)
        report = tracker.report()
        assert report.paraphrase_variance is not None
        assert report.paraphrase_variance > 0


class TestEffectiveScoreIntegration:
    """Tests for effective_score integration in optimizer accept/reject."""

    async def test_effective_score_used_when_variance_computed(self) -> None:
        """Optimizer should use effective_score when variance is computed."""
        config = AgentConfig(system_prompt="Basic.")
        test_suite = TestSuite(
            tests=[
                TestCase(id="t1", input="Say hello", expected="hello", eval_mode="exact_match"),
                TestCase(id="t2", input="Say bye", expected="bye", eval_mode="exact_match"),
            ]
        )

        call_idx = 0

        def respond(messages: list[Message]) -> str:
            nonlocal call_idx
            system = messages[0].content if messages and messages[0].role == "system" else ""
            user = messages[-1].content if messages else ""

            if "optimization strategist" in system.lower():
                return json.dumps({
                    "mutation_type": "prompt.rewrite",
                    "rationale": "Improve prompt",
                    "target_tests": [],
                    "target_components": ["system_prompt"],
                    "params": {},
                })

            if "prompt optimization expert" in system.lower():
                return "IMPROVED: Reply with the exact expected word."

            if "IMPROVED" in system:
                if "hello" in user.lower():
                    return "hello"
                if "bye" in user.lower():
                    return "bye"
            return "I don't know"

        llm = MockLLM(responses=respond)

        with tempfile.TemporaryDirectory() as tmp:
            opt_config = OptimizerConfig(
                max_iterations=2,
                target_score=1.0,
                n_eval_runs=3,  # Multiple runs to compute variance
                compute_ci=False,
                variance_lambda=0.1,
                variance_modes=["run"],
            )
            optimizer = Optimizer(
                config=config,
                test_suite=test_suite,
                llm=llm,
                opt_config=opt_config,
                history_path=Path(tmp) / "history.jsonl",
            )

            result = await optimizer.run()
            # Should complete without error
            assert result is not None

    def test_effective_score_calculation(self) -> None:
        """effective_score should return mean - lambda * variance."""
        result = effective_score(0.8, 0.1, lam=0.5)
        assert abs(result - 0.75) < 1e-6  # 0.8 - 0.5 * 0.1 = 0.75

    def test_effective_score_zero_variance(self) -> None:
        """With zero variance, effective_score equals mean."""
        result = effective_score(0.9, 0.0, lam=0.5)
        assert abs(result - 0.9) < 1e-6
