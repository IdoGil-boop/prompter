"""Tests for mutation base — registry, MutationResult, MutationProposal."""
from __future__ import annotations

import pytest

from prompter.config.agent_config import AgentConfig
from prompter.eval.evaluator import EvalReport
from prompter.mutations.base import (
    Mutation,
    MutationContext,
    MutationProposal,
    MutationResult,
    _MUTATION_REGISTRY,
    register_mutation,
)


class TestMutationRegistry:
    def test_prompt_rewrite_registered(self) -> None:
        """SystemPromptMutation should be in registry after import."""
        import prompter.mutations.prompt  # noqa: F401

        registry = Mutation.registry()
        assert "prompt.rewrite" in registry

    def test_register_mutation_decorator(self) -> None:
        """register_mutation should add class to registry."""
        initial_count = len(_MUTATION_REGISTRY)

        @register_mutation
        class TestMutation(Mutation):
            type_id = "__test_mutation__"
            cost_tier = 99

            async def apply(self, context, proposal):
                return MutationResult(
                    config=context.config,
                    description="test",
                    mutation_type=self.type_id,
                    components_touched=[],
                )

        assert "__test_mutation__" in _MUTATION_REGISTRY
        # Clean up
        del _MUTATION_REGISTRY["__test_mutation__"]


class TestMutationContext:
    def test_context_creation(self) -> None:
        config = AgentConfig(system_prompt="P")
        report = EvalReport(config_id="x", aggregate_score=0.5, results=[])
        ctx = MutationContext(config=config, eval_report=report, history=[])
        assert ctx.config.system_prompt == "P"
        assert ctx.eval_report.aggregate_score == 0.5
        assert ctx.attribution_hints == {}


class TestMutationProposal:
    def test_proposal_creation(self) -> None:
        proposal = MutationProposal(
            mutation_type="prompt.rewrite",
            rationale="Improve",
            target_tests=["t1"],
            target_components=["system_prompt"],
            cost_tier=1,
        )
        assert proposal.mutation_type == "prompt.rewrite"
        assert proposal.cost_tier == 1


class TestMutationResult:
    def test_result_creation(self) -> None:
        config = AgentConfig(system_prompt="New prompt")
        result = MutationResult(
            config=config,
            description="Rewrote prompt",
            mutation_type="prompt.rewrite",
            components_touched=["system_prompt"],
        )
        assert result.config.system_prompt == "New prompt"
        assert result.mutation_type == "prompt.rewrite"
