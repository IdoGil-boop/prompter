"""Tests for SystemPromptMutation — prompt rewrite with mock LLM."""
from __future__ import annotations

import pytest

from prompter.config.agent_config import AgentConfig
from prompter.eval.evaluator import EvalReport, TestResult
from prompter.mutations.base import MutationContext, MutationProposal, MutationResult
from prompter.mutations.prompt import SystemPromptMutation
from tests.conftest import MockLLM


class TestSystemPromptMutation:
    async def test_applies_prompt_rewrite(self) -> None:
        """Mutation should produce a new config with rewritten system prompt."""
        llm = MockLLM(responses=["You are an improved assistant that gives exact answers."])
        mutation = SystemPromptMutation(llm)

        config = AgentConfig(system_prompt="You are a basic assistant.")
        report = EvalReport(
            config_id="test",
            aggregate_score=0.3,
            results=[
                TestResult(test_id="t1", score=0.0, actual_output="wrong"),
            ],
        )
        context = MutationContext(config=config, eval_report=report, history=[])
        proposal = MutationProposal(
            mutation_type="prompt.rewrite",
            rationale="Improve accuracy",
            target_tests=["t1"],
            target_components=["system_prompt"],
            cost_tier=1,
        )

        result = await mutation.apply(context, proposal)

        assert isinstance(result, MutationResult)
        assert result.mutation_type == "prompt.rewrite"
        assert result.config.system_prompt != config.system_prompt
        assert "improved" in result.config.system_prompt.lower()
        assert "system_prompt" in result.components_touched

    async def test_strips_markdown_fences(self) -> None:
        """If LLM wraps response in ```, mutation should strip them."""
        llm = MockLLM(responses=["```\nClean prompt\n```"])
        mutation = SystemPromptMutation(llm)

        config = AgentConfig(system_prompt="Old")
        report = EvalReport(config_id="x", aggregate_score=0.0, results=[])
        context = MutationContext(config=config, eval_report=report, history=[])
        proposal = MutationProposal(
            mutation_type="prompt.rewrite",
            rationale="fix",
            target_tests=[],
            target_components=["system_prompt"],
            cost_tier=1,
        )

        result = await mutation.apply(context, proposal)
        assert "```" not in result.config.system_prompt

    def test_type_id(self) -> None:
        assert SystemPromptMutation.type_id == "prompt.rewrite"
        assert SystemPromptMutation.cost_tier == 1
