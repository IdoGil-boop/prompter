"""Tests for model escalation — tier progression, early exit."""
from __future__ import annotations

import pytest

from prompter.llm.adapter import LLMResponse, Message, TokenUsage, ToolDefinition
from prompter.llm.escalation import EscalationResult, ModelEscalation
from tests.conftest import MockLLM


class TestModelEscalation:
    async def test_accept_when_improving(self) -> None:
        """Accept mutation when score improves across tiers."""
        local_llm = MockLLM(responses=["ok"])
        cheap_llm = MockLLM(responses=["ok"])

        escalation = ModelEscalation(
            tiers={"local": local_llm, "cheap": cheap_llm},
            improvement_threshold=0.01,
        )

        async def eval_fn(adapter):
            return 0.8  # Better than baseline

        result = await escalation.validate(eval_fn, baseline_score=0.5)
        assert result.accepted is True
        assert result.tier_reached == "cheap"

    async def test_reject_on_regression(self) -> None:
        """Reject early if regression detected at any tier."""
        local_llm = MockLLM(responses=["ok"])
        cheap_llm = MockLLM(responses=["ok"])

        escalation = ModelEscalation(
            tiers={"local": local_llm, "cheap": cheap_llm},
            regression_threshold=-0.02,
        )

        async def eval_fn(adapter):
            return 0.3  # Regression from baseline 0.5

        result = await escalation.validate(eval_fn, baseline_score=0.5)
        assert result.accepted is False
        assert result.rejection_tier == "local"

    async def test_reject_insufficient_improvement(self) -> None:
        """Reject when improvement is below threshold."""
        llm = MockLLM(responses=["ok"])
        escalation = ModelEscalation(
            tiers={"local": llm},
            improvement_threshold=0.1,
        )

        async def eval_fn(adapter):
            return 0.52  # Only 0.02 improvement, below 0.1 threshold

        result = await escalation.validate(eval_fn, baseline_score=0.5)
        assert result.accepted is False

    def test_no_tiers_raises(self) -> None:
        with pytest.raises(ValueError, match="At least one"):
            ModelEscalation(tiers={})

    async def test_scores_by_tier_populated(self) -> None:
        local_llm = MockLLM(responses=["ok"])
        escalation = ModelEscalation(tiers={"local": local_llm})

        async def eval_fn(adapter):
            return 0.9

        result = await escalation.validate(eval_fn, baseline_score=0.5)
        assert "local" in result.scores_by_tier
