"""Tests for LLM adapter protocol conformance."""
from __future__ import annotations

from prompter.llm.adapter import (
    LLMAdapter,
    Message,
    TokenUsage,
    ToolCall,
    ToolDefinition,
)
from tests.conftest import MockLLM


class TestLLMAdapterProtocol:
    def test_mock_llm_satisfies_protocol(self) -> None:
        """MockLLM should be recognized as LLMAdapter."""
        llm = MockLLM(responses=["test"])
        assert isinstance(llm, LLMAdapter)

    async def test_mock_llm_complete(self) -> None:
        llm = MockLLM(responses=["hello"])
        result = await llm.complete([Message(role="user", content="hi")])
        assert result.content == "hello"
        assert result.usage.total_tokens == 20

    async def test_mock_llm_callable_responses(self) -> None:
        def respond(messages: list[Message]) -> str:
            return f"echo: {messages[-1].content}"

        llm = MockLLM(responses=respond)
        result = await llm.complete([Message(role="user", content="test")])
        assert result.content == "echo: test"

    def test_mock_llm_properties(self) -> None:
        llm = MockLLM(responses=[])
        assert llm.model_id == "mock"
        assert llm.tier == "local"


class TestMessage:
    def test_to_dict_basic(self) -> None:
        msg = Message(role="user", content="hello")
        d = msg.to_dict()
        assert d["role"] == "user"
        assert d["content"] == "hello"

    def test_to_dict_with_tool_calls(self) -> None:
        tc = ToolCall(id="1", name="search", arguments={"q": "test"})
        msg = Message(role="assistant", content="", tool_calls=[tc])
        d = msg.to_dict()
        assert "tool_calls" in d
        assert len(d["tool_calls"]) == 1


class TestTokenUsage:
    def test_total_tokens(self) -> None:
        usage = TokenUsage(prompt_tokens=100, completion_tokens=50)
        assert usage.total_tokens == 150

    def test_default_zero(self) -> None:
        usage = TokenUsage()
        assert usage.total_tokens == 0


class TestToolDefinition:
    def test_to_dict(self) -> None:
        td = ToolDefinition(
            name="search",
            description="Search web",
            parameters={"type": "object"},
        )
        d = td.to_dict()
        assert d["type"] == "function"
        assert d["function"]["name"] == "search"
