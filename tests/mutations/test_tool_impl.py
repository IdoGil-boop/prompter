"""Tests for ToolImplementationMutation — rewrites tool implementation code."""
from __future__ import annotations

from prompter.config.agent_config import AgentConfig, ToolSpec
from prompter.eval.evaluator import EvalReport, TestResult
from prompter.mutations.base import MutationContext, MutationProposal, MutationResult
from prompter.mutations.tool_impl import ToolImplementationMutation
from tests.conftest import MockLLM


class TestToolImplementationMutation:
    async def test_rewrites_tool_implementation(self) -> None:
        """Mutation should produce a new config with updated tool code."""
        new_impl = (
            "import json, sys\n"
            "args = json.loads(sys.stdin.read())\n"
            "print(args['a'] + args['b'])"
        )
        llm = MockLLM(responses=[new_impl])
        mutation = ToolImplementationMutation(llm)

        config = AgentConfig(
            system_prompt="Use tools.",
            tools={
                "add": ToolSpec(
                    name="add",
                    description="Add two numbers",
                    parameters_schema={
                        "type": "object",
                        "properties": {"a": {"type": "number"}, "b": {"type": "number"}},
                    },
                    implementation="print('wrong')",
                ),
            },
        )
        report = EvalReport(
            config_id="test",
            aggregate_score=0.2,
            results=[TestResult(test_id="t1", score=0.0, actual_output="wrong")],
        )
        context = MutationContext(config=config, eval_report=report, history=[])
        proposal = MutationProposal(
            mutation_type="tool_impl.modify",
            rationale="Fix tool implementation",
            target_tests=["t1"],
            target_components=["tool:add"],
            cost_tier=4,
            params={"tool_name": "add"},
        )

        result = await mutation.apply(context, proposal)

        assert isinstance(result, MutationResult)
        assert result.mutation_type == "tool_impl.modify"
        assert "tool:add" in result.components_touched
        assert result.config.tools["add"].implementation != "print('wrong')"

    async def test_rejects_invalid_syntax(self) -> None:
        """Mutation should reject code with syntax errors."""
        bad_code = "def broken(\n  missing closing paren"
        llm = MockLLM(responses=[bad_code])
        mutation = ToolImplementationMutation(llm)

        config = AgentConfig(
            system_prompt="Use tools.",
            tools={
                "calc": ToolSpec(
                    name="calc",
                    description="Calculate",
                    parameters_schema={},
                    implementation="print('old')",
                ),
            },
        )
        report = EvalReport(config_id="x", aggregate_score=0.0, results=[])
        context = MutationContext(config=config, eval_report=report, history=[])
        proposal = MutationProposal(
            mutation_type="tool_impl.modify",
            rationale="fix",
            target_tests=[],
            target_components=["tool:calc"],
            cost_tier=4,
            params={"tool_name": "calc"},
        )

        # Should raise because syntax is invalid
        import pytest

        with pytest.raises(ValueError, match="syntax"):
            await mutation.apply(context, proposal)

    async def test_preserves_tool_description(self) -> None:
        """Mutation should not change tool description."""
        new_impl = "print('new')"
        llm = MockLLM(responses=[new_impl])
        mutation = ToolImplementationMutation(llm)

        config = AgentConfig(
            system_prompt="Agent",
            tools={
                "tool1": ToolSpec(
                    name="tool1",
                    description="Original description",
                    parameters_schema={},
                    implementation="print('old')",
                ),
            },
        )
        report = EvalReport(config_id="x", aggregate_score=0.0, results=[])
        context = MutationContext(config=config, eval_report=report, history=[])
        proposal = MutationProposal(
            mutation_type="tool_impl.modify",
            rationale="fix",
            target_tests=[],
            target_components=["tool:tool1"],
            cost_tier=4,
            params={"tool_name": "tool1"},
        )

        result = await mutation.apply(context, proposal)
        assert result.config.tools["tool1"].description == "Original description"

    def test_type_id_and_cost_tier(self) -> None:
        assert ToolImplementationMutation.type_id == "tool_impl.modify"
        assert ToolImplementationMutation.cost_tier == 4
