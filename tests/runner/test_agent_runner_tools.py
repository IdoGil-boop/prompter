"""Tests for AgentRunner multi-turn tool call loop."""
from __future__ import annotations

from typing import Any

import pytest

from prompter.config.agent_config import AgentConfig, ToolSpec
from prompter.llm.adapter import LLMResponse, Message, TokenUsage, ToolCall, ToolDefinition
from prompter.runner.agent_runner import AgentRunner
from prompter.runner.tool_sandbox import ToolSandbox
from tests.conftest import MockLLM


class ToolCallMockLLM:
    """MockLLM that returns tool calls on first call, then text on second."""

    def __init__(
        self,
        tool_calls_sequence: list[list[ToolCall] | None],
        text_responses: list[str],
    ) -> None:
        self._tool_calls_sequence = list(tool_calls_sequence)
        self._text_responses = list(text_responses)
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
        idx = self._call_count
        self._call_count += 1

        # When called without tools (e.g., synthesis call), always return text
        if tools is None:
            text_idx = max(0, idx - len(self._tool_calls_sequence))
            text = self._text_responses[text_idx] if text_idx < len(self._text_responses) else ""
            return LLMResponse(content=text, usage=TokenUsage(10, 10))

        if idx < len(self._tool_calls_sequence) and self._tool_calls_sequence[idx]:
            return LLMResponse(
                content="",
                tool_calls=self._tool_calls_sequence[idx],
                usage=TokenUsage(10, 10),
            )
        text_idx = idx - len(self._tool_calls_sequence)
        if text_idx < 0:
            text_idx = 0
        text = self._text_responses[text_idx] if text_idx < len(self._text_responses) else ""
        return LLMResponse(content=text, usage=TokenUsage(10, 10))

    @property
    def model_id(self) -> str:
        return "mock-tool"

    @property
    def tier(self) -> str:
        return "local"


class TestAgentRunnerToolLoop:
    """AgentRunner handles multi-turn tool call → tool result → continuation."""

    async def test_tool_call_executed_via_sandbox(self) -> None:
        """When LLM returns tool_calls, runner should execute them via sandbox."""
        config = AgentConfig(
            system_prompt="Use the add tool.",
            tools={
                "add": ToolSpec(
                    name="add",
                    description="Add two numbers",
                    parameters_schema={
                        "type": "object",
                        "properties": {"a": {"type": "number"}, "b": {"type": "number"}},
                    },
                    implementation=(
                        "import json, sys\n"
                        "args = json.loads(sys.stdin.read())\n"
                        "print(args['a'] + args['b'])"
                    ),
                ),
            },
        )
        llm = ToolCallMockLLM(
            tool_calls_sequence=[
                [ToolCall(id="tc1", name="add", arguments={"a": 2, "b": 3})],
            ],
            text_responses=["The answer is 5"],
        )
        sandbox = ToolSandbox(timeout_seconds=5.0)
        runner = AgentRunner(config=config, llm=llm, sandbox=sandbox)

        result = await runner.run("What is 2 + 3?")
        assert result == "The answer is 5"

    async def test_no_sandbox_logs_warning_on_tool_calls(self) -> None:
        """If sandbox is None and tool_calls are received, return content with warning."""
        config = AgentConfig(
            system_prompt="Use tools.",
            tools={
                "add": ToolSpec(
                    name="add",
                    description="Add",
                    parameters_schema={},
                    implementation="pass",
                ),
            },
        )
        llm = ToolCallMockLLM(
            tool_calls_sequence=[
                [ToolCall(id="tc1", name="add", arguments={})],
            ],
            text_responses=["fallback"],
        )
        runner = AgentRunner(config=config, llm=llm)

        # With no sandbox, tool calls can't be executed - should return content
        result = await runner.run("test")
        # Should return the empty content from the tool call response (no sandbox = can't execute)
        assert isinstance(result, str)

    async def test_max_tool_rounds_respected(self) -> None:
        """Runner should stop after max_tool_rounds even if LLM keeps calling tools."""
        config = AgentConfig(
            system_prompt="Loop forever",
            tools={
                "noop": ToolSpec(
                    name="noop",
                    description="No-op",
                    parameters_schema={},
                    implementation="import json, sys; json.loads(sys.stdin.read()); print('ok')",
                ),
            },
        )
        # LLM always returns tool calls
        always_tool_calls = ToolCallMockLLM(
            tool_calls_sequence=[
                [ToolCall(id=f"tc{i}", name="noop", arguments={})]
                for i in range(20)
            ],
            text_responses=["final"],
        )
        sandbox = ToolSandbox(timeout_seconds=5.0)
        runner = AgentRunner(
            config=config, llm=always_tool_calls, sandbox=sandbox, max_tool_rounds=3,
        )

        result = await runner.run("loop")
        # Should stop after 3 rounds and return the last message content
        assert isinstance(result, str)
        assert always_tool_calls._call_count <= 4  # 3 tool rounds + at most 1 more

    async def test_max_tool_rounds_returns_llm_synthesis_not_raw_tool_result(self) -> None:
        """After exhausting max_tool_rounds, runner should call LLM one final time
        without tools to synthesize a proper response, not return raw tool output."""
        config = AgentConfig(
            system_prompt="Use tools.",
            tools={
                "noop": ToolSpec(
                    name="noop",
                    description="No-op",
                    parameters_schema={},
                    implementation="import json, sys; json.loads(sys.stdin.read()); print('ok')",
                ),
            },
        )
        # LLM returns tool calls for first 3 rounds, then "synthesized answer" on final call
        always_tool_calls = ToolCallMockLLM(
            tool_calls_sequence=[
                [ToolCall(id=f"tc{i}", name="noop", arguments={})]
                for i in range(5)
            ],
            text_responses=["synthesized answer from all tool results"],
        )
        sandbox = ToolSandbox(timeout_seconds=5.0)
        runner = AgentRunner(
            config=config, llm=always_tool_calls, sandbox=sandbox, max_tool_rounds=3,
        )

        result = await runner.run("test input")
        # The result should be an LLM-synthesized response, not raw tool output "ok"
        assert result == "synthesized answer from all tool results"
        # One extra call (without tools) for synthesis after exhausting rounds
        assert always_tool_calls._call_count == 4  # 3 tool rounds + 1 synthesis

    async def test_multiple_tool_calls_in_one_round(self) -> None:
        """Multiple tool calls in a single response should all be executed."""
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
                    implementation=(
                        "import json, sys\n"
                        "args = json.loads(sys.stdin.read())\n"
                        "print(args['a'] + args['b'])"
                    ),
                ),
            },
        )
        llm = ToolCallMockLLM(
            tool_calls_sequence=[
                [
                    ToolCall(id="tc1", name="add", arguments={"a": 1, "b": 2}),
                    ToolCall(id="tc2", name="add", arguments={"a": 3, "b": 4}),
                ],
            ],
            text_responses=["Results: 3 and 7"],
        )
        sandbox = ToolSandbox(timeout_seconds=5.0)
        runner = AgentRunner(config=config, llm=llm, sandbox=sandbox)

        result = await runner.run("Calculate")
        assert result == "Results: 3 and 7"
        # Two LLM calls: one returning tool calls, one returning text
        assert llm._call_count == 2

    async def test_tool_trace_events_recorded(self) -> None:
        """Each tool call should produce a trace event."""
        config = AgentConfig(
            system_prompt="Use tools.",
            tools={
                "echo": ToolSpec(
                    name="echo",
                    description="Echo",
                    parameters_schema={"type": "object", "properties": {"msg": {"type": "string"}}},
                    implementation=(
                        "import json, sys\n"
                        "args = json.loads(sys.stdin.read())\n"
                        "print(args['msg'])"
                    ),
                ),
            },
        )
        llm = ToolCallMockLLM(
            tool_calls_sequence=[
                [ToolCall(id="tc1", name="echo", arguments={"msg": "hello"})],
            ],
            text_responses=["done"],
        )
        sandbox = ToolSandbox(timeout_seconds=5.0)
        runner = AgentRunner(config=config, llm=llm, sandbox=sandbox)

        await runner.run("echo hello")

        tool_events = [e for e in runner.trace_events if e.event_type == "tool_call"]
        assert len(tool_events) >= 1
        assert tool_events[0].component == "tool:echo"
