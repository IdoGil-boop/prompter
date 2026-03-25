"""Tests for ConfigValueMutation — adjusts config values."""
from __future__ import annotations

import json

from prompter.config.agent_config import AgentConfig
from prompter.eval.evaluator import EvalReport, TestResult
from prompter.mutations.base import MutationContext, MutationProposal, MutationResult
from prompter.mutations.config_value import ConfigValueMutation
from tests.conftest import MockLLM


class TestConfigValueMutation:
    async def test_adjusts_rag_config(self) -> None:
        """Mutation should update rag_config based on LLM suggestion."""
        new_config_json = json.dumps({"chunk_size": 512, "top_k": 5})
        llm = MockLLM(responses=[new_config_json])
        mutation = ConfigValueMutation(llm)

        config = AgentConfig(
            system_prompt="Agent",
            rag_config={"chunk_size": 256, "top_k": 3},
        )
        report = EvalReport(
            config_id="test",
            aggregate_score=0.4,
            results=[TestResult(test_id="t1", score=0.0, actual_output="wrong")],
        )
        context = MutationContext(config=config, eval_report=report, history=[])
        proposal = MutationProposal(
            mutation_type="config.adjust",
            rationale="Increase context window",
            target_tests=["t1"],
            target_components=["rag_config"],
            cost_tier=3,
            params={"target": "rag_config"},
        )

        result = await mutation.apply(context, proposal)

        assert isinstance(result, MutationResult)
        assert result.mutation_type == "config.adjust"
        assert result.config.rag_config == {"chunk_size": 512, "top_k": 5}

    async def test_adjusts_context_strategy(self) -> None:
        """Mutation should update context_strategy."""
        new_config_json = json.dumps({"window_size": 10})
        llm = MockLLM(responses=[new_config_json])
        mutation = ConfigValueMutation(llm)

        config = AgentConfig(
            system_prompt="Agent",
            context_strategy={"window_size": 5},
        )
        report = EvalReport(config_id="x", aggregate_score=0.0, results=[])
        context = MutationContext(config=config, eval_report=report, history=[])
        proposal = MutationProposal(
            mutation_type="config.adjust",
            rationale="Increase window",
            target_tests=[],
            target_components=["context_strategy"],
            cost_tier=3,
            params={"target": "context_strategy"},
        )

        result = await mutation.apply(context, proposal)
        assert result.config.context_strategy == {"window_size": 10}

    async def test_adjusts_memory_strategy(self) -> None:
        """Mutation should update memory_strategy."""
        new_config_json = json.dumps({"max_entries": 200})
        llm = MockLLM(responses=[new_config_json])
        mutation = ConfigValueMutation(llm)

        config = AgentConfig(
            system_prompt="Agent",
            memory_strategy={"max_entries": 100},
        )
        report = EvalReport(config_id="x", aggregate_score=0.0, results=[])
        context = MutationContext(config=config, eval_report=report, history=[])
        proposal = MutationProposal(
            mutation_type="config.adjust",
            rationale="More memory",
            target_tests=[],
            target_components=["memory_strategy"],
            cost_tier=3,
            params={"target": "memory_strategy"},
        )

        result = await mutation.apply(context, proposal)
        assert result.config.memory_strategy == {"max_entries": 200}

    def test_type_id_and_cost_tier(self) -> None:
        assert ConfigValueMutation.type_id == "config.adjust"
        assert ConfigValueMutation.cost_tier == 3

    async def test_invalid_json_raises_valueerror_with_context(self) -> None:
        """_parse_json in config_value should raise ValueError with mutation context."""
        llm = MockLLM(responses=["this is not json"])
        mutation = ConfigValueMutation(llm)

        config = AgentConfig(
            system_prompt="Agent",
            rag_config={"chunk_size": 256},
        )
        report = EvalReport(
            config_id="test",
            aggregate_score=0.4,
            results=[TestResult(test_id="t1", score=0.0, actual_output="wrong")],
        )
        context = MutationContext(config=config, eval_report=report, history=[])
        proposal = MutationProposal(
            mutation_type="config.adjust",
            rationale="Adjust config",
            target_tests=["t1"],
            target_components=["rag_config"],
            cost_tier=3,
            params={"target": "rag_config"},
        )

        import pytest

        with pytest.raises(ValueError, match="Failed to parse LLM response"):
            await mutation.apply(context, proposal)
