"""Tests for bootstrap CI computation."""
from __future__ import annotations

import pytest

from prompter.eval.bootstrap import BootstrapResult, bootstrap_ci, bootstrap_delta


class TestBootstrapCI:
    def test_basic_ci(self) -> None:
        scores = [0.8, 0.9, 0.85, 0.75, 0.95]
        result = bootstrap_ci(scores, rng_seed=42)
        assert isinstance(result, BootstrapResult)
        assert 0.0 <= result.ci_lower <= result.mean <= result.ci_upper <= 1.0
        assert result.n_samples == 5
        assert result.confidence_level == 0.95

    def test_single_value(self) -> None:
        result = bootstrap_ci([1.0], rng_seed=42)
        assert result.mean == 1.0
        assert result.ci_lower == 1.0
        assert result.ci_upper == 1.0

    def test_empty_raises(self) -> None:
        with pytest.raises(ValueError, match="empty"):
            bootstrap_ci([])

    def test_ci_width_property(self) -> None:
        result = bootstrap_ci([0.5, 0.6, 0.7, 0.8, 0.9], rng_seed=42)
        assert result.ci_width == pytest.approx(result.ci_upper - result.ci_lower)

    def test_significance_vs_zero(self) -> None:
        # All positive scores -> CI should be above zero
        result = bootstrap_ci([0.8, 0.9, 0.85, 0.95], rng_seed=42)
        assert result.is_significant_vs_zero is True


class TestBootstrapDelta:
    def test_positive_delta(self) -> None:
        before = [0.3, 0.4, 0.35]
        after = [0.8, 0.9, 0.85]
        result = bootstrap_delta(before, after, rng_seed=42)
        assert result.mean > 0
        assert result.ci_lower > 0  # Significant improvement

    def test_no_difference(self) -> None:
        scores = [0.5, 0.5, 0.5]
        result = bootstrap_delta(scores, scores, rng_seed=42)
        assert result.mean == pytest.approx(0.0)

    def test_negative_delta(self) -> None:
        before = [0.8, 0.9, 0.85]
        after = [0.3, 0.4, 0.35]
        result = bootstrap_delta(before, after, rng_seed=42)
        assert result.mean < 0
