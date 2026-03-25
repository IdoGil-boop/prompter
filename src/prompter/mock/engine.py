"""MockEngine — injects mock capabilities for hypothesis testing."""
from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, Literal

from prompter.config.agent_config import ToolSpec
from prompter.runner.agent_runner import AgentRunner

if TYPE_CHECKING:
    from collections.abc import Callable

    from prompter.config.agent_config import AgentConfig
    from prompter.eval.evaluator import Evaluator
    from prompter.eval.test_suite import TestSuite
    from prompter.llm.adapter import LLMAdapter

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class MockCapability:
    """A hypothetical capability to test via mock injection."""

    name: str
    description: str
    mock_output_fn: Callable[[str], str] | str
    capability_type: Literal["tool", "rag", "context"]


@dataclass(frozen=True)
class MockTestResult:
    """Result of a hypothesis test comparing baseline vs mock-injected config."""

    capability: MockCapability
    baseline_score: float
    mock_score: float
    delta: float
    is_significant: bool
    target_outputs: dict[str, str]


class MockEngine:
    """Injects mock capabilities into an agent config for hypothesis testing."""

    def __init__(self, significance_threshold: float = 0.05) -> None:
        self._significance_threshold = significance_threshold

    def inject(
        self, config: AgentConfig, mock: MockCapability
    ) -> AgentConfig:
        """Create config with the mock capability wired in."""
        if mock.capability_type == "tool":
            return self._inject_tool(config, mock)
        if mock.capability_type == "rag":
            return self._inject_rag(config, mock)
        if mock.capability_type == "context":
            return self._inject_context(config, mock)
        raise ValueError(f"Unknown capability type: {mock.capability_type}")

    async def test_hypothesis(
        self,
        config: AgentConfig,
        mock: MockCapability,
        test_suite: TestSuite,
        evaluator: Evaluator,
        llm: LLMAdapter,
    ) -> MockTestResult:
        """Does adding this mock capability improve the score?"""
        # 1. Evaluate baseline config
        baseline_runner = AgentRunner(config=config, llm=llm)
        baseline_report = await evaluator.evaluate(
            agent_fn=baseline_runner.as_agent_fn(),
            test_suite=test_suite,
            config_id="baseline",
        )
        baseline_score = baseline_report.aggregate_score

        # 2. Build mock agent fn that uses mock output for test inputs
        target_outputs: dict[str, str] = {}
        for test in test_suite.tests:
            if callable(mock.mock_output_fn):
                mock_out = mock.mock_output_fn(test.input)
            else:
                mock_out = mock.mock_output_fn
            target_outputs[test.id] = mock_out

        # Create an agent function that returns mock outputs
        mock_outputs_by_input = {
            test.input: target_outputs[test.id] for test in test_suite.tests
        }

        async def mock_agent_fn(
            input_text: str, context: dict[str, Any] | None = None
        ) -> str:
            return mock_outputs_by_input.get(input_text, "")

        # 4. Evaluate mock config
        mock_report = await evaluator.evaluate(
            agent_fn=mock_agent_fn,
            test_suite=test_suite,
            config_id="mock",
        )
        mock_score = mock_report.aggregate_score

        # 5. Compute delta and significance
        delta = mock_score - baseline_score
        is_significant = delta > self._significance_threshold

        logger.info(
            "Hypothesis test for '%s': baseline=%.4f, mock=%.4f, "
            "delta=%.4f, significant=%s",
            mock.name, baseline_score, mock_score,
            delta, is_significant,
        )

        return MockTestResult(
            capability=mock,
            baseline_score=baseline_score,
            mock_score=mock_score,
            delta=delta,
            is_significant=is_significant,
            target_outputs=target_outputs,
        )

    def _inject_tool(
        self, config: AgentConfig, mock: MockCapability
    ) -> AgentConfig:
        """Create a ToolSpec from the mock and add to config."""
        if callable(mock.mock_output_fn):
            impl = (
                "import sys, json\n"
                "data = json.load(sys.stdin)\n"
                f"# Mock implementation for {mock.name}\n"
                "print(json.dumps('mock_output'))"
            )
        else:
            impl = (
                "import sys, json\n"
                f"print(json.dumps({mock.mock_output_fn!r}))"
            )

        tool_spec = ToolSpec(
            name=mock.name,
            description=mock.description,
            parameters_schema={
                "type": "object",
                "properties": {"input": {"type": "string"}},
            },
            implementation=impl,
            enabled=True,
        )
        return config.with_tool(mock.name, tool_spec)

    def _inject_rag(
        self, config: AgentConfig, mock: MockCapability
    ) -> AgentConfig:
        """Inject a mock RAG config."""
        mock_output = (
            mock.mock_output_fn
            if isinstance(mock.mock_output_fn, str)
            else "mock_rag_output"
        )
        rag_config: dict[str, Any] = {
            "mock_name": mock.name,
            "description": mock.description,
            "mock_output": mock_output,
            "type": "mock",
        }
        return config.with_rag_config(rag_config)

    def _inject_context(
        self, config: AgentConfig, mock: MockCapability
    ) -> AgentConfig:
        """Inject a mock context strategy."""
        mock_output = (
            mock.mock_output_fn
            if isinstance(mock.mock_output_fn, str)
            else "mock_context_output"
        )
        context_strategy: dict[str, Any] = {
            "mock_name": mock.name,
            "description": mock.description,
            "mock_output": mock_output,
            "type": "mock",
        }
        return config.with_context_strategy(context_strategy)
