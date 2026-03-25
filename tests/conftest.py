"""Shared test fixtures: MockLLM, sample configs, sample test suites."""
from __future__ import annotations

import tempfile
from pathlib import Path
from typing import TYPE_CHECKING

import pytest

from prompter.config.agent_config import AgentConfig, ToolSpec
from prompter.eval.test_suite import TestCase, TestSuite
from prompter.llm.adapter import LLMResponse, Message, TokenUsage, ToolDefinition

if TYPE_CHECKING:
    from collections.abc import Callable


class MockLLM:
    """Deterministic LLMAdapter for testing. Returns predefined responses."""

    def __init__(
        self,
        responses: list[str] | Callable[[list[Message]], str],
    ) -> None:
        self._responses = responses
        self._call_log: list[list[Message]] = []

    async def complete(
        self,
        messages: list[Message],
        tools: list[ToolDefinition] | None = None,
        temperature: float = 0.0,
        max_tokens: int = 4096,
    ) -> LLMResponse:
        self._call_log.append(messages)
        content = self._responses(messages) if callable(self._responses) else self._responses.pop(0)
        return LLMResponse(content=content, usage=TokenUsage(10, 10))

    @property
    def model_id(self) -> str:
        return "mock"

    @property
    def tier(self) -> str:
        return "local"


@pytest.fixture
def mock_llm() -> MockLLM:
    """A MockLLM that echoes the user message."""
    def echo(messages: list[Message]) -> str:
        user_msgs = [m for m in messages if m.role == "user"]
        return user_msgs[-1].content if user_msgs else ""
    return MockLLM(responses=echo)


@pytest.fixture
def sample_config() -> AgentConfig:
    """A minimal agent config for testing."""
    return AgentConfig(
        system_prompt="You are a helpful assistant.",
    )


@pytest.fixture
def sample_config_with_tools() -> AgentConfig:
    """Agent config with tools for testing."""
    return AgentConfig(
        system_prompt="You are a helpful assistant with tools.",
        tools={
            "search": ToolSpec(
                name="search",
                description="Search the web for information",
                parameters_schema={"type": "object", "properties": {"query": {"type": "string"}}},
                implementation="def search(query): return 'result'",
            ),
        },
    )


@pytest.fixture
def sample_test_suite() -> TestSuite:
    """A small test suite with exact match tests."""
    return TestSuite(
        tests=[
            TestCase(id="t1", input="Say hello", expected="hello", eval_mode="exact_match"),
            TestCase(id="t2", input="Say goodbye", expected="goodbye", eval_mode="exact_match"),
            TestCase(id="t3", input="Say yes", expected="yes", eval_mode="exact_match"),
        ],
    )


@pytest.fixture
def tmp_agent_dir(sample_config: AgentConfig) -> Path:
    """Create a temporary agent directory with a system prompt file."""
    with tempfile.TemporaryDirectory() as d:
        path = Path(d)
        sample_config.save(path)
        yield path


@pytest.fixture
def tmp_test_suite_file(sample_test_suite: TestSuite) -> Path:
    """Create a temporary test suite YAML file."""
    with tempfile.TemporaryDirectory() as d:
        path = Path(d) / "tests.yaml"
        sample_test_suite.save(path)
        yield path
