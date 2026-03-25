"""Tests for MockEngine — mock injection and hypothesis testing."""
from __future__ import annotations

from typing import Any

import pytest

from prompter.config.agent_config import AgentConfig, ToolSpec
from prompter.eval.evaluator import Evaluator
from prompter.eval.test_suite import TestCase, TestSuite
from prompter.mock.engine import MockCapability, MockEngine, MockTestResult
from tests.conftest import MockLLM


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def engine() -> MockEngine:
    return MockEngine(significance_threshold=0.05)


@pytest.fixture
def base_config() -> AgentConfig:
    return AgentConfig(system_prompt="You are a helpful assistant.")


@pytest.fixture
def config_with_tools() -> AgentConfig:
    return AgentConfig(
        system_prompt="You are an assistant with tools.",
        tools={
            "search": ToolSpec(
                name="search",
                description="Search the web",
                parameters_schema={"type": "object", "properties": {"q": {"type": "string"}}},
                implementation="import sys, json; print(json.dumps('result'))",
            ),
        },
    )


@pytest.fixture
def small_suite() -> TestSuite:
    return TestSuite(tests=[
        TestCase(id="t1", input="What is 2+2?", expected="4", eval_mode="exact_match"),
        TestCase(id="t2", input="What is 3+3?", expected="6", eval_mode="exact_match"),
    ])


# ---------------------------------------------------------------------------
# MockCapability dataclass
# ---------------------------------------------------------------------------

class TestMockCapability:
    def test_create_tool_capability_with_static_string(self) -> None:
        cap = MockCapability(
            name="calculator",
            description="Performs arithmetic",
            mock_output_fn="42",
            capability_type="tool",
        )
        assert cap.name == "calculator"
        assert cap.capability_type == "tool"
        assert cap.mock_output_fn == "42"

    def test_create_tool_capability_with_callable(self) -> None:
        cap = MockCapability(
            name="calculator",
            description="Performs arithmetic",
            mock_output_fn=lambda inp: str(eval(inp)),
            capability_type="tool",
        )
        assert callable(cap.mock_output_fn)

    def test_capability_is_frozen(self) -> None:
        cap = MockCapability(
            name="calc", description="desc",
            mock_output_fn="42", capability_type="tool",
        )
        with pytest.raises(AttributeError):
            cap.name = "other"  # type: ignore[misc]

    def test_capability_types(self) -> None:
        for ct in ("tool", "rag", "context"):
            cap = MockCapability(
                name="x", description="x",
                mock_output_fn="x", capability_type=ct,
            )
            assert cap.capability_type == ct


# ---------------------------------------------------------------------------
# MockEngine.inject
# ---------------------------------------------------------------------------

class TestMockEngineInject:
    def test_inject_tool_creates_tool_in_config(
        self, engine: MockEngine, base_config: AgentConfig,
    ) -> None:
        cap = MockCapability(
            name="calculator", description="Math tool",
            mock_output_fn="42", capability_type="tool",
        )
        injected = engine.inject(base_config, cap)

        assert "calculator" in injected.tools
        assert injected.tools["calculator"].description == "Math tool"
        # Original config unchanged (frozen)
        assert "calculator" not in base_config.tools

    def test_inject_tool_with_callable_output(
        self, engine: MockEngine, base_config: AgentConfig,
    ) -> None:
        cap = MockCapability(
            name="calc", description="Calculator",
            mock_output_fn=lambda inp: "result",
            capability_type="tool",
        )
        injected = engine.inject(base_config, cap)
        assert "calc" in injected.tools
        # Implementation should be set (non-empty)
        assert injected.tools["calc"].implementation

    def test_inject_rag_sets_rag_config(
        self, engine: MockEngine, base_config: AgentConfig,
    ) -> None:
        cap = MockCapability(
            name="knowledge_base", description="RAG source",
            mock_output_fn="relevant context chunk",
            capability_type="rag",
        )
        injected = engine.inject(base_config, cap)
        assert injected.rag_config is not None
        assert injected.rag_config["mock_name"] == "knowledge_base"
        # Original unchanged
        assert base_config.rag_config is None

    def test_inject_context_sets_context_strategy(
        self, engine: MockEngine, base_config: AgentConfig,
    ) -> None:
        cap = MockCapability(
            name="user_history", description="Context injection",
            mock_output_fn="prior conversation context",
            capability_type="context",
        )
        injected = engine.inject(base_config, cap)
        assert injected.context_strategy is not None
        assert injected.context_strategy["mock_name"] == "user_history"

    def test_inject_preserves_existing_tools(
        self, engine: MockEngine, config_with_tools: AgentConfig,
    ) -> None:
        cap = MockCapability(
            name="calculator", description="Math",
            mock_output_fn="42", capability_type="tool",
        )
        injected = engine.inject(config_with_tools, cap)
        assert "search" in injected.tools
        assert "calculator" in injected.tools


# ---------------------------------------------------------------------------
# MockEngine.test_hypothesis
# ---------------------------------------------------------------------------

class TestMockEngineHypothesis:
    async def test_hypothesis_returns_mock_test_result(
        self, engine: MockEngine, base_config: AgentConfig, small_suite: TestSuite,
    ) -> None:
        """Mock capability that always returns correct answer should improve score."""
        # LLM returns wrong answers normally
        llm = MockLLM(responses=lambda msgs: "wrong answer")

        # Mock that returns correct answers
        cap = MockCapability(
            name="oracle", description="Provides perfect answers",
            mock_output_fn=lambda inp: "4" if "2+2" in inp else "6",
            capability_type="tool",
        )
        evaluator = Evaluator(n_runs=1)

        result = await engine.test_hypothesis(
            config=base_config,
            mock=cap,
            test_suite=small_suite,
            evaluator=evaluator,
            llm=llm,
        )

        assert isinstance(result, MockTestResult)
        assert result.capability.name == "oracle"
        assert result.baseline_score >= 0.0
        assert result.mock_score >= 0.0
        assert isinstance(result.delta, float)
        assert isinstance(result.is_significant, bool)
        assert isinstance(result.target_outputs, dict)

    async def test_hypothesis_significance_check(
        self, engine: MockEngine, base_config: AgentConfig, small_suite: TestSuite,
    ) -> None:
        """When mock improves score significantly, is_significant should be True."""
        # Baseline LLM always wrong
        llm = MockLLM(responses=lambda msgs: "wrong")

        # Mock with correct outputs
        cap = MockCapability(
            name="oracle", description="Oracle",
            mock_output_fn=lambda inp: "4" if "2+2" in inp else "6",
            capability_type="tool",
        )
        evaluator = Evaluator(n_runs=1)

        result = await engine.test_hypothesis(
            config=base_config, mock=cap,
            test_suite=small_suite, evaluator=evaluator, llm=llm,
        )

        # Baseline score should be 0 (always wrong), mock should be higher
        assert result.delta > 0.0
        assert result.is_significant is True

    async def test_hypothesis_no_improvement(
        self, engine: MockEngine, base_config: AgentConfig, small_suite: TestSuite,
    ) -> None:
        """When mock doesn't improve score, is_significant should be False."""
        # LLM already returns correct answers
        llm = MockLLM(responses=lambda msgs: (
            "4" if "2+2" in msgs[-1].content else "6"
        ))

        # Mock provides same quality
        cap = MockCapability(
            name="useless", description="No help",
            mock_output_fn="wrong answer",
            capability_type="tool",
        )
        evaluator = Evaluator(n_runs=1)

        result = await engine.test_hypothesis(
            config=base_config, mock=cap,
            test_suite=small_suite, evaluator=evaluator, llm=llm,
        )

        # Mock doesn't help — delta should not be significant
        assert result.is_significant is False

    async def test_hypothesis_captures_target_outputs(
        self, engine: MockEngine, base_config: AgentConfig, small_suite: TestSuite,
    ) -> None:
        """target_outputs should map test_id -> mock output for each test."""
        llm = MockLLM(responses=lambda msgs: "wrong")

        cap = MockCapability(
            name="oracle", description="Oracle",
            mock_output_fn=lambda inp: "answer_" + inp[:5],
            capability_type="tool",
        )
        evaluator = Evaluator(n_runs=1)

        result = await engine.test_hypothesis(
            config=base_config, mock=cap,
            test_suite=small_suite, evaluator=evaluator, llm=llm,
        )

        assert "t1" in result.target_outputs
        assert "t2" in result.target_outputs


# ---------------------------------------------------------------------------
# MockTestResult dataclass
# ---------------------------------------------------------------------------

class TestMockTestResult:
    def test_result_is_frozen(self) -> None:
        cap = MockCapability(
            name="x", description="x",
            mock_output_fn="x", capability_type="tool",
        )
        result = MockTestResult(
            capability=cap,
            baseline_score=0.5,
            mock_score=0.8,
            delta=0.3,
            is_significant=True,
            target_outputs={"t1": "answer"},
        )
        with pytest.raises(AttributeError):
            result.delta = 0.0  # type: ignore[misc]
