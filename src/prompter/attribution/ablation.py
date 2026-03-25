"""AblationSweep — removes one component at a time, measures impact on score."""
from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import TYPE_CHECKING

from prompter.runner.agent_runner import AgentRunner

if TYPE_CHECKING:
    from prompter.config.agent_config import AgentConfig
    from prompter.eval.evaluator import Evaluator
    from prompter.eval.test_suite import TestSuite
    from prompter.llm.adapter import LLMAdapter

logger = logging.getLogger(__name__)

GENERIC_SYSTEM_PROMPT = "You are a helpful assistant."


@dataclass(frozen=True)
class AblationResult:
    """Result of an ablation sweep over config components."""

    component_deltas: dict[str, float]  # component -> score_delta (positive = helpful)
    baseline_score: float


class AblationSweep:
    """Removes one component at a time, measures impact on score.

    For each component in config.component_names():
    - Create ablated config (without that component)
    - Evaluate ablated config
    - Delta = original_score - ablated_score
    - Positive delta = component helps; negative = component hurts
    """

    async def run(
        self,
        config: AgentConfig,
        test_suite: TestSuite,
        evaluator: Evaluator,
        llm: LLMAdapter,
    ) -> AblationResult:
        """Run ablation sweep, returning deltas for each component."""
        # Evaluate baseline
        baseline_runner = AgentRunner(config=config, llm=llm)
        baseline_report = await evaluator.evaluate(
            agent_fn=baseline_runner.as_agent_fn(),
            test_suite=test_suite,
            config_id="ablation_baseline",
        )
        baseline_score = baseline_report.aggregate_score

        component_deltas: dict[str, float] = {}

        for component in config.component_names():
            ablated = self._ablate_component(config, component)
            runner = AgentRunner(config=ablated, llm=llm)
            report = await evaluator.evaluate(
                agent_fn=runner.as_agent_fn(),
                test_suite=test_suite,
                config_id=f"ablation_{component}",
            )
            delta = baseline_score - report.aggregate_score
            component_deltas[component] = delta

            logger.info(
                "Ablation %s: %.4f -> %.4f (delta: %+.4f)",
                component,
                baseline_score,
                report.aggregate_score,
                delta,
            )

        return AblationResult(
            component_deltas=component_deltas,
            baseline_score=baseline_score,
        )

    def _ablate_component(self, config: AgentConfig, component: str) -> AgentConfig:
        """Create a config with the given component removed or neutralized."""
        if component == "system_prompt":
            return config.with_system_prompt(GENERIC_SYSTEM_PROMPT)
        elif component.startswith("tool:"):
            tool_name = component[len("tool:"):]
            return config.without_tool(tool_name)
        elif component == "rag_config":
            return config.with_rag_config(None)
        elif component == "context_strategy":
            return config.with_context_strategy(None)
        elif component == "memory_strategy":
            return config.with_memory_strategy(None)
        else:
            logger.warning("Unknown component for ablation: %s", component)
            return config
