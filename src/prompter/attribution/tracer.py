"""TraceAttributor — estimates component contribution from execution traces."""
from __future__ import annotations

import logging
from collections import Counter
from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from prompter.eval.evaluator import TestResult, TraceEvent

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class TraceAttribution:
    """Attribution scores for each component based on trace analysis."""

    component_scores: dict[str, float]


class TraceAttributor:
    """Estimates component contribution from execution traces.

    Logic: Components that appear in failing traces get attribution
    proportional to (1 - score) * (appearance_count / total_events).
    Passing tests (score=1.0) produce zero attribution.
    """

    def attribute(
        self, trace: list[TraceEvent], test_result: TestResult
    ) -> TraceAttribution:
        """Compute attribution scores for components in a single test trace.

        Components appearing in failing tests get higher scores.
        Score is weighted by failure severity (1 - test_score).
        """
        if not trace:
            return TraceAttribution(component_scores={})

        failure_weight = 1.0 - test_result.score
        if failure_weight <= 0:
            return TraceAttribution(component_scores={})

        # Count how many times each component appears
        component_counts: Counter[str] = Counter()
        for event in trace:
            component_counts[event.component] += 1

        total_events = sum(component_counts.values())
        if total_events == 0:
            return TraceAttribution(component_scores={})

        # Attribution = failure_weight * (count / total)
        scores: dict[str, float] = {}
        for component, count in component_counts.items():
            scores[component] = failure_weight * (count / total_events)

        return TraceAttribution(component_scores=scores)
