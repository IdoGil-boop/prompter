"""Integration test: optimizer with tool-using agent end-to-end."""
from __future__ import annotations

import json
import tempfile
from pathlib import Path
from typing import Any

import pytest

from prompter.config.agent_config import AgentConfig, ToolSpec
from prompter.eval.test_suite import TestCase, TestSuite
from prompter.llm.adapter import LLMResponse, Message, TokenUsage, ToolCall, ToolDefinition
from prompter.optimizer import Optimizer, OptimizerConfig
from prompter.runner.tool_sandbox import ToolSandbox


class ToolAwareMockLLM:
    """MockLLM that simulates a tool-using agent and optimizer LLM.

    Agent behavior: When tools are available, calls calculate tool.
    Optimizer behavior: When asked to rewrite prompts, returns improved version.
    """

    def __init__(self) -> None:
        self._call_count = 0
        self._call_log: list[list[Message]] = []

    async def complete(
        self,
        messages: list[Message],
        tools: list[ToolDefinition] | None = None,
        temperature: float = 0.0,
        max_tokens: int = 4096,
    ) -> LLMResponse:
        self._call_log.append(messages)
        self._call_count += 1

        system_content = messages[0].content if messages else ""
        user_content = next((m.content for m in messages if m.role == "user"), "")

        # Optimizer/proposer: propose prompt.rewrite mutation
        if "analyze test failures" in system_content.lower() or "failure" in system_content.lower():
            return LLMResponse(
                content=json.dumps({
                    "mutation_type": "prompt.rewrite",
                    "rationale": "Improve system prompt to handle calculations better",
                    "target_tests": ["t1"],
                    "target_components": ["system_prompt"],
                    "cost_tier": 1,
                }),
                usage=TokenUsage(10, 10),
            )

        # Optimizer/mutator: rewrite system prompt
        if "prompt optimization" in system_content.lower():
            return LLMResponse(
                content="You are a calculator. Always use the calculate tool for math. Return the numeric result.",
                usage=TokenUsage(10, 10),
            )

        # Agent with tools: check if this is a tool result continuation
        tool_results = [m for m in messages if m.role == "tool"]
        if tool_results:
            # Return the tool result as the final answer
            return LLMResponse(
                content=tool_results[-1].content.strip(),
                usage=TokenUsage(10, 10),
            )

        # Agent: if tools available and user asks a math question, call calculate
        if tools and ("+" in user_content or "add" in user_content.lower()):
            # Parse simple "X + Y" or return a tool call
            return LLMResponse(
                content="",
                tool_calls=[
                    ToolCall(
                        id=f"tc_{self._call_count}",
                        name="calculate",
                        arguments={"expression": user_content.strip()},
                    ),
                ],
                usage=TokenUsage(10, 10),
            )

        # Default: echo
        return LLMResponse(content=user_content, usage=TokenUsage(10, 10))

    @property
    def model_id(self) -> str:
        return "tool-mock"

    @property
    def tier(self) -> str:
        return "local"


class TestOptimizerWithTools:
    """Integration: optimizer runs with a tool-using agent."""

    async def test_optimizer_runs_with_tool_agent(self) -> None:
        """Optimizer should be able to run iterations with a tool-using agent."""
        config = AgentConfig(
            system_prompt="You are an assistant.",
            tools={
                "calculate": ToolSpec(
                    name="calculate",
                    description="Evaluate a math expression",
                    parameters_schema={
                        "type": "object",
                        "properties": {
                            "expression": {"type": "string"},
                        },
                    },
                    implementation=(
                        "import json, sys\n"
                        "args = json.loads(sys.stdin.read())\n"
                        "try:\n"
                        "    result = eval(args['expression'])\n"
                        "    print(result)\n"
                        "except Exception as e:\n"
                        "    print(f'Error: {e}')\n"
                    ),
                ),
            },
        )

        test_suite = TestSuite(
            tests=[
                TestCase(
                    id="t1",
                    input="2 + 3",
                    expected="5",
                    eval_mode="exact_match",
                ),
            ],
        )

        llm = ToolAwareMockLLM()

        with tempfile.TemporaryDirectory() as tmp:
            history_path = Path(tmp) / "history.jsonl"

            optimizer = Optimizer(
                config=config,
                test_suite=test_suite,
                llm=llm,
                opt_config=OptimizerConfig(
                    max_iterations=2,
                    n_eval_runs=1,
                    compute_ci=False,
                ),
                history_path=history_path,
            )

            result = await optimizer.run()

            # Should complete without errors
            assert result.best_config is not None
            assert result.iterations_run >= 0
            assert result.baseline_report is not None
            assert result.final_report is not None

    async def test_all_mutation_types_registered(self) -> None:
        """All Phase 2 mutation types should be in the registry."""
        from prompter.mutations.base import Mutation

        registry = Mutation.registry()

        expected_types = [
            "prompt.rewrite",
            "tool_desc.edit",
            "config.adjust",
            "tool_impl.modify",
            "tool.add",
            "tool.remove",
        ]

        for mt in expected_types:
            assert mt in registry, f"Mutation type '{mt}' not registered"
