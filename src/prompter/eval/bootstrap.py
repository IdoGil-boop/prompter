from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

import numpy as np

if TYPE_CHECKING:
    from numpy.typing import NDArray

logger = logging.getLogger(__name__)

DEFAULT_N_BOOTSTRAP = 1000
DEFAULT_CONFIDENCE_LEVEL = 0.95


@dataclass(frozen=True)
class BootstrapResult:
    mean: float
    ci_lower: float
    ci_upper: float
    std: float
    n_samples: int
    n_bootstrap: int
    confidence_level: float

    @property
    def ci_width(self) -> float:
        return self.ci_upper - self.ci_lower

    @property
    def is_significant_vs_zero(self) -> bool:
        """True if the entire CI is above (or below) zero."""
        return self.ci_lower > 0 or self.ci_upper < 0


def bootstrap_ci(
    scores: list[float] | NDArray[np.floating[Any]],
    confidence_level: float = DEFAULT_CONFIDENCE_LEVEL,
    n_bootstrap: int = DEFAULT_N_BOOTSTRAP,
    rng_seed: int | None = None,
) -> BootstrapResult:
    """Bootstrap confidence interval for the mean of scores."""
    arr = np.asarray(scores, dtype=np.float64)
    if len(arr) == 0:
        raise ValueError("Cannot bootstrap empty scores array")

    rng = np.random.default_rng(rng_seed)
    boot_means = np.empty(n_bootstrap)

    for i in range(n_bootstrap):
        sample = rng.choice(arr, size=len(arr), replace=True)
        boot_means[i] = sample.mean()

    alpha = 1 - confidence_level
    ci_lower = float(np.percentile(boot_means, 100 * alpha / 2))
    ci_upper = float(np.percentile(boot_means, 100 * (1 - alpha / 2)))

    return BootstrapResult(
        mean=float(arr.mean()),
        ci_lower=ci_lower,
        ci_upper=ci_upper,
        std=float(arr.std()),
        n_samples=len(arr),
        n_bootstrap=n_bootstrap,
        confidence_level=confidence_level,
    )


def bootstrap_delta(
    scores_before: list[float] | NDArray[np.floating[Any]],
    scores_after: list[float] | NDArray[np.floating[Any]],
    confidence_level: float = DEFAULT_CONFIDENCE_LEVEL,
    n_bootstrap: int = DEFAULT_N_BOOTSTRAP,
    rng_seed: int | None = None,
) -> BootstrapResult:
    """Bootstrap CI for the difference in means (after - before)."""
    before = np.asarray(scores_before, dtype=np.float64)
    after = np.asarray(scores_after, dtype=np.float64)

    rng = np.random.default_rng(rng_seed)
    boot_deltas = np.empty(n_bootstrap)

    for i in range(n_bootstrap):
        sample_b = rng.choice(before, size=len(before), replace=True)
        sample_a = rng.choice(after, size=len(after), replace=True)
        boot_deltas[i] = sample_a.mean() - sample_b.mean()

    alpha = 1 - confidence_level
    ci_lower = float(np.percentile(boot_deltas, 100 * alpha / 2))
    ci_upper = float(np.percentile(boot_deltas, 100 * (1 - alpha / 2)))

    return BootstrapResult(
        mean=float(after.mean() - before.mean()),
        ci_lower=ci_lower,
        ci_upper=ci_upper,
        std=float(boot_deltas.std()),
        n_samples=min(len(before), len(after)),
        n_bootstrap=n_bootstrap,
        confidence_level=confidence_level,
    )
