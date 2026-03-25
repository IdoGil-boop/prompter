"""Tests for ToolDescriptionMutation — rewrites tool description."""
from __future__ import annotations

from prompter.config.agent_config import AgentConfig, ToolSpec
from prompter.eval.evaluator import EvalReport, TestResult
from prompter.mutations.base import MutationContext, MutationProposal, MutationResult
from prompter.mutations.tool_desc import ToolDescriptionMutation
from tests.conftest import MockLLM


class TestToolDescriptionMutation:
    async def test_rewrites_tool_description(self) -> None:
        """Mutation should produce a new config with updated tool description."""
        llm = MockLLM(responses=["Search the web for real-time information using keywords."])
        mutation = ToolDescriptionMutation(llm)

        config = AgentConfig(
            system_prompt="Use tools.",
            tools={
                "search": ToolSpec(
                    name="search",
                    description="Search stuff",
                    parameters_schema={"type": "object", "properties": {"q": {"type": "string"}}},
                    implementation="pass",
                ),
            },
        )
        report = EvalReport(
            config_id="test",
            aggregate_score=0.3,
            results=[TestResult(test_id="t1", score=0.0, actual_output="wrong")],
        )
        context = MutationContext(config=config, eval_report=report, history=[])
        proposal = MutationProposal(
            mutation_type="tool_desc.edit",
            rationale="Tool description is vague",
            target_tests=["t1"],
            target_components=["tool:search"],
            cost_tier=2,
            params={"tool_name": "search"},
        )

        result = await mutation.apply(context, proposal)

        assert isinstance(result, MutationResult)
        assert result.mutation_type == "tool_desc.edit"
        assert "tool:search" in result.components_touched
        new_desc = result.config.tools["search"].description
        assert new_desc != "Search stuff"
        assert "search" in new_desc.lower() or "Search" in new_desc

    async def test_preserves_tool_implementation(self) -> None:
        """Mutation should not change tool implementation."""
        llm = MockLLM(responses=["Better description"])
        mutation = ToolDescriptionMutation(llm)

        original_impl = "def search(q): return 'result'"
        config = AgentConfig(
            system_prompt="Use tools.",
            tools={
                "search": ToolSpec(
                    name="search",
                    description="Old description",
                    parameters_schema={},
                    implementation=original_impl,
                ),
            },
        )
        report = EvalReport(config_id="x", aggregate_score=0.0, results=[])
        context = MutationContext(config=config, eval_report=report, history=[])
        proposal = MutationProposal(
            mutation_type="tool_desc.edit",
            rationale="fix",
            target_tests=[],
            target_components=["tool:search"],
            cost_tier=2,
            params={"tool_name": "search"},
        )

        result = await mutation.apply(context, proposal)
        assert result.config.tools["search"].implementation == original_impl

    def test_type_id_and_cost_tier(self) -> None:
        assert ToolDescriptionMutation.type_id == "tool_desc.edit"
        assert ToolDescriptionMutation.cost_tier == 2
