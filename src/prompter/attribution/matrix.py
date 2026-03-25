"""AttributionMatrix — Component x TestCase attribution scores."""
from __future__ import annotations

import logging
from collections import defaultdict
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from prompter.attribution.ablation import AblationResult
    from prompter.attribution.tracer import TraceAttribution

logger = logging.getLogger(__name__)


@dataclass
class AttributionMatrix:
    """Component x TestCase attribution scores.

    Combines trace-based and ablation-based attribution into a unified matrix.
    Used to identify top suspect components for targeted mutation.
    """

    matrix: dict[str, dict[str, float]] = field(
        default_factory=lambda: defaultdict(dict)
    )

    def merge_trace(self, trace_attr: TraceAttribution, test_id: str) -> None:
        """Merge a single test's trace attribution into the matrix."""
        for component, score in trace_attr.component_scores.items():
            self.matrix[component][test_id] = score

    def merge_ablation(self, ablation: AblationResult) -> None:
        """Merge ablation results into the matrix under '_ablation' key."""
        for component, delta in ablation.component_deltas.items():
            self.matrix[component]["_ablation"] = delta

    def top_suspects(self, n: int = 3) -> list[str]:
        """Components most likely causing failures, ranked by aggregate score.

        Aggregate = mean of all scores (trace + ablation) for each component.
        """
        if not self.matrix:
            return []

        aggregates: dict[str, float] = {}
        for component, scores in self.matrix.items():
            if scores:
                aggregates[component] = sum(scores.values()) / len(scores)
            else:
                aggregates[component] = 0.0

        ranked = sorted(aggregates.items(), key=lambda x: x[1], reverse=True)
        return [component for component, _score in ranked[:n]]

    def as_hints(self) -> dict[str, float]:
        """Convert to flat dict for MutationContext.attribution_hints.

        Returns mean score per component.
        """
        hints: dict[str, float] = {}
        for component, scores in self.matrix.items():
            if scores:
                hints[component] = sum(scores.values()) / len(scores)
        return hints
