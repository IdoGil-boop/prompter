"""Tests for AddToolMutation and RemoveToolMutation."""
from __future__ import annotations

import json

from prompter.config.agent_config import AgentConfig, ToolSpec
from prompter.eval.evaluator import EvalReport, TestResult
from prompter.mutations.base import MutationContext, MutationProposal, MutationResult
from prompter.mutations.tool_manage import AddToolMutation, RemoveToolMutation
from tests.conftest import MockLLM


class TestAddToolMutation:
    async def test_adds_new_tool(self) -> None:
        """Mutation should add a new tool to the config."""
        tool_json = json.dumps({
            "name": "multiply",
            "description": "Multiply two numbers",
            "parameters_schema": {
                "type": "object",
                "properties": {
                    "a": {"type": "number"},
                    "b": {"type": "number"},
                },
            },
            "implementation": (
                "import json, sys\n"
                "args = json.loads(sys.stdin.read())\n"
                "print(args['a'] * args['b'])"
            ),
        })
        llm = MockLLM(responses=[tool_json])
        mutation = AddToolMutation(llm)

        config = AgentConfig(system_prompt="Calculator agent.")
        report = EvalReport(
            config_id="test",
            aggregate_score=0.3,
            results=[TestResult(test_id="t1", score=0.0, actual_output="wrong")],
        )
        context = MutationContext(config=config, eval_report=report, history=[])
        proposal = MutationProposal(
            mutation_type="tool.add",
            rationale="Need multiplication tool",
            target_tests=["t1"],
            target_components=[],
            cost_tier=5,
        )

        result = await mutation.apply(context, proposal)

        assert isinstance(result, MutationResult)
        assert result.mutation_type == "tool.add"
        assert "multiply" in result.config.tools
        assert result.config.tools["multiply"].description == "Multiply two numbers"

    async def test_rejects_empty_implementation(self) -> None:
        """AddToolMutation should raise ValueError if LLM returns empty implementation."""
        tool_json = json.dumps({
            "name": "broken_tool",
            "description": "A tool with no implementation",
            "parameters_schema": {"type": "object"},
            "implementation": "",
        })
        llm = MockLLM(responses=[tool_json])
        mutation = AddToolMutation(llm)

        config = AgentConfig(system_prompt="Agent.")
        report = EvalReport(
            config_id="test",
            aggregate_score=0.3,
            results=[TestResult(test_id="t1", score=0.0, actual_output="wrong")],
        )
        context = MutationContext(config=config, eval_report=report, history=[])
        proposal = MutationProposal(
            mutation_type="tool.add",
            rationale="Need a tool",
            target_tests=["t1"],
            target_components=[],
            cost_tier=5,
        )

        import pytest

        with pytest.raises(ValueError, match="empty implementation"):
            await mutation.apply(context, proposal)

    async def test_rejects_missing_implementation_key(self) -> None:
        """AddToolMutation should raise ValueError if implementation key is omitted."""
        tool_json = json.dumps({
            "name": "no_impl_tool",
            "description": "Missing implementation key",
            "parameters_schema": {"type": "object"},
        })
        llm = MockLLM(responses=[tool_json])
        mutation = AddToolMutation(llm)

        config = AgentConfig(system_prompt="Agent.")
        report = EvalReport(
            config_id="test",
            aggregate_score=0.3,
            results=[TestResult(test_id="t1", score=0.0, actual_output="wrong")],
        )
        context = MutationContext(config=config, eval_report=report, history=[])
        proposal = MutationProposal(
            mutation_type="tool.add",
            rationale="Need a tool",
            target_tests=["t1"],
            target_components=[],
            cost_tier=5,
        )

        import pytest

        with pytest.raises(ValueError, match="empty implementation"):
            await mutation.apply(context, proposal)

    def test_type_id_and_cost_tier(self) -> None:
        assert AddToolMutation.type_id == "tool.add"
        assert AddToolMutation.cost_tier == 5


class TestRemoveToolMutation:
    async def test_removes_existing_tool(self) -> None:
        """Mutation should remove a tool from the config."""
        llm = MockLLM(responses=["unused_tool"])
        mutation = RemoveToolMutation(llm)

        config = AgentConfig(
            system_prompt="Agent with tools.",
            tools={
                "useful": ToolSpec(
                    name="useful",
                    description="Useful tool",
                    parameters_schema={},
                    implementation="print('useful')",
                ),
                "unused_tool": ToolSpec(
                    name="unused_tool",
                    description="Never used",
                    parameters_schema={},
                    implementation="print('unused')",
                ),
            },
        )
        report = EvalReport(
            config_id="test",
            aggregate_score=0.5,
            results=[TestResult(test_id="t1", score=0.0, actual_output="wrong")],
        )
        context = MutationContext(config=config, eval_report=report, history=[])
        proposal = MutationProposal(
            mutation_type="tool.remove",
            rationale="Tool is never used and may confuse the LLM",
            target_tests=["t1"],
            target_components=["tool:unused_tool"],
            cost_tier=5,
            params={"tool_name": "unused_tool"},
        )

        result = await mutation.apply(context, proposal)

        assert isinstance(result, MutationResult)
        assert result.mutation_type == "tool.remove"
        assert "unused_tool" not in result.config.tools
        assert "useful" in result.config.tools

    async def test_remove_nonexistent_tool_raises(self) -> None:
        """Removing a tool that doesn't exist should raise ValueError."""
        llm = MockLLM(responses=["ghost_tool"])
        mutation = RemoveToolMutation(llm)

        config = AgentConfig(system_prompt="Agent.")
        report = EvalReport(config_id="x", aggregate_score=0.0, results=[])
        context = MutationContext(config=config, eval_report=report, history=[])
        proposal = MutationProposal(
            mutation_type="tool.remove",
            rationale="Remove tool",
            target_tests=[],
            target_components=["tool:ghost_tool"],
            cost_tier=5,
            params={"tool_name": "ghost_tool"},
        )

        import pytest

        with pytest.raises(ValueError, match="not found"):
            await mutation.apply(context, proposal)

    def test_type_id_and_cost_tier(self) -> None:
        assert RemoveToolMutation.type_id == "tool.remove"
        assert RemoveToolMutation.cost_tier == 5


class TestParseJsonToolManage:
    async def test_invalid_json_raises_valueerror_with_context(self) -> None:
        """_parse_json in tool_manage should raise ValueError with mutation context."""
        llm = MockLLM(responses=["not valid json {{{"])
        mutation = AddToolMutation(llm)

        config = AgentConfig(system_prompt="Agent.")
        report = EvalReport(
            config_id="test",
            aggregate_score=0.3,
            results=[TestResult(test_id="t1", score=0.0, actual_output="wrong")],
        )
        context = MutationContext(config=config, eval_report=report, history=[])
        proposal = MutationProposal(
            mutation_type="tool.add",
            rationale="Need a tool",
            target_tests=["t1"],
            target_components=[],
            cost_tier=5,
        )

        import pytest

        with pytest.raises(ValueError, match="Failed to parse LLM response"):
            await mutation.apply(context, proposal)
