"""Tests for AgentRunner — wraps AgentConfig + LLMAdapter into AgentFn."""
from __future__ import annotations

import pytest

from prompter.config.agent_config import AgentConfig, ToolSpec
from prompter.runner.agent_runner import AgentRunner
from tests.conftest import MockLLM


class TestAgentRunner:
    """AgentRunner constructs messages and delegates to LLM."""

    async def test_run_sends_system_and_user_messages(self) -> None:
        """Runner should construct [system, user] messages from config + input."""
        llm = MockLLM(responses=["hello world"])
        config = AgentConfig(system_prompt="You are helpful.")
        runner = AgentRunner(config=config, llm=llm)

        result = await runner.run("Say hello")

        assert result == "hello world"
        assert len(llm._call_log) == 1
        messages = llm._call_log[0]
        assert messages[0].role == "system"
        assert messages[0].content == "You are helpful."
        assert messages[1].role == "user"
        assert messages[1].content == "Say hello"

    async def test_run_with_tools_includes_tool_definitions(self) -> None:
        """When config has tools, runner should pass ToolDefinitions to LLM."""
        tools_passed: list = []

        class CaptureLLM(MockLLM):
            async def complete(self, messages, tools=None, **kw):
                tools_passed.append(tools)
                return await super().complete(messages, tools, **kw)

        config = AgentConfig(
            system_prompt="Helper",
            tools={
                "search": ToolSpec(
                    name="search",
                    description="Search the web",
                    parameters_schema={"type": "object", "properties": {"q": {"type": "string"}}},
                    implementation="",
                ),
            },
        )
        llm = CaptureLLM(responses=["search result"])
        runner = AgentRunner(config=config, llm=llm)

        await runner.run("find something")

        assert len(tools_passed) == 1
        assert tools_passed[0] is not None
        assert len(tools_passed[0]) == 1
        assert tools_passed[0][0].name == "search"

    async def test_run_without_tools_passes_none(self) -> None:
        """When config has no tools, runner should pass tools=None."""
        tools_passed: list = []

        class CaptureLLM(MockLLM):
            async def complete(self, messages, tools=None, **kw):
                tools_passed.append(tools)
                return await super().complete(messages, tools, **kw)

        config = AgentConfig(system_prompt="Helper")
        llm = CaptureLLM(responses=["ok"])
        runner = AgentRunner(config=config, llm=llm)

        await runner.run("hi")

        assert tools_passed[0] is None

    async def test_as_agent_fn_returns_callable(self) -> None:
        """as_agent_fn() should return a callable matching the AgentFn protocol."""
        llm = MockLLM(responses=["response"])
        config = AgentConfig(system_prompt="You are helpful.")
        runner = AgentRunner(config=config, llm=llm)

        agent_fn = runner.as_agent_fn()
        result = await agent_fn("test input")

        assert result == "response"

    async def test_as_agent_fn_accepts_context(self) -> None:
        """AgentFn callable should accept optional context parameter."""
        llm = MockLLM(responses=["response"])
        config = AgentConfig(system_prompt="You are helpful.")
        runner = AgentRunner(config=config, llm=llm)

        agent_fn = runner.as_agent_fn()
        result = await agent_fn("test input", context={"key": "value"})

        assert result == "response"

    async def test_trace_events_stored(self) -> None:
        """Runner should store trace events for attribution."""
        llm = MockLLM(responses=["output"])
        config = AgentConfig(system_prompt="Prompt")
        runner = AgentRunner(config=config, llm=llm)

        await runner.run("input")

        assert len(runner.trace_events) >= 1
        event = runner.trace_events[0]
        assert event.event_type == "llm_call"
        assert event.component == "system_prompt"

    async def test_only_enabled_tools_included(self) -> None:
        """Disabled tools should not be passed to the LLM."""
        tools_passed: list = []

        class CaptureLLM(MockLLM):
            async def complete(self, messages, tools=None, **kw):
                tools_passed.append(tools)
                return await super().complete(messages, tools, **kw)

        config = AgentConfig(
            system_prompt="Helper",
            tools={
                "search": ToolSpec(
                    name="search",
                    description="Search",
                    parameters_schema={},
                    implementation="",
                    enabled=True,
                ),
                "disabled_tool": ToolSpec(
                    name="disabled_tool",
                    description="Disabled",
                    parameters_schema={},
                    implementation="",
                    enabled=False,
                ),
            },
        )
        llm = CaptureLLM(responses=["ok"])
        runner = AgentRunner(config=config, llm=llm)

        await runner.run("test")

        assert len(tools_passed[0]) == 1
        assert tools_passed[0][0].name == "search"
