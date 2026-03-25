from __future__ import annotations

import logging
from dataclasses import dataclass, field

import numpy as np

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class VarianceReport:
    run_variance: float
    order_variance: float | None = None
    condensation_variance: float | None = None
    paraphrase_variance: float | None = None

    @property
    def total_variance(self) -> float:
        components = [self.run_variance]
        if self.order_variance is not None:
            components.append(self.order_variance)
        if self.condensation_variance is not None:
            components.append(self.condensation_variance)
        if self.paraphrase_variance is not None:
            components.append(self.paraphrase_variance)
        return float(np.mean(components))


def compute_run_variance(scores_per_run: list[list[float]]) -> float:
    """Variance across repeated runs of the same test suite."""
    run_means = [float(np.mean(scores)) for scores in scores_per_run]
    return float(np.var(run_means))


def effective_score(mean_score: float, variance: float, lam: float = 0.1) -> float:
    """Score penalized by variance: effective = mean - λ * variance."""
    return mean_score - lam * variance


@dataclass
class VarianceTracker:
    """Accumulates scores across multiple variance axes."""

    run_scores: list[list[float]] = field(default_factory=list)
    order_scores: list[float] = field(default_factory=list)
    paraphrase_scores: list[float] = field(default_factory=list)

    def add_run(self, scores: list[float]) -> None:
        self.run_scores.append(scores)

    def add_order_variant(self, score: float) -> None:
        self.order_scores.append(score)

    def add_paraphrase_variant(self, score: float) -> None:
        self.paraphrase_scores.append(score)

    def report(self) -> VarianceReport:
        run_var = compute_run_variance(self.run_scores) if len(self.run_scores) >= 2 else 0.0
        order_var = float(np.var(self.order_scores)) if len(self.order_scores) >= 2 else None
        paraphrase_var = (
            float(np.var(self.paraphrase_scores))
            if len(self.paraphrase_scores) >= 2
            else None
        )

        return VarianceReport(
            run_variance=run_var,
            order_variance=order_var,
            paraphrase_variance=paraphrase_var,
        )
