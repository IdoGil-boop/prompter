"""Tests for variance tracking and effective_score."""
from __future__ import annotations

import pytest

from prompter.eval.variance import VarianceReport, VarianceTracker, compute_run_variance, effective_score


class TestEffectiveScore:
    def test_no_variance_penalty(self) -> None:
        assert effective_score(0.8, 0.0) == 0.8

    def test_with_variance_penalty(self) -> None:
        result = effective_score(0.8, 0.1, lam=0.1)
        assert result == pytest.approx(0.79)

    def test_high_variance_lowers_score(self) -> None:
        assert effective_score(0.8, 1.0, lam=0.5) < effective_score(0.8, 0.0, lam=0.5)


class TestVarianceTracker:
    def test_single_run_zero_variance(self) -> None:
        tracker = VarianceTracker()
        tracker.add_run([0.5, 0.6, 0.7])
        report = tracker.report()
        assert report.run_variance == 0.0  # Need 2+ runs

    def test_multiple_runs_nonzero_variance(self) -> None:
        tracker = VarianceTracker()
        tracker.add_run([0.5, 0.5, 0.5])
        tracker.add_run([0.9, 0.9, 0.9])
        report = tracker.report()
        assert report.run_variance > 0.0

    def test_order_variance_tracking(self) -> None:
        tracker = VarianceTracker()
        tracker.add_order_variant(0.5)
        tracker.add_order_variant(0.8)
        report = tracker.report()
        assert report.order_variance is not None
        assert report.order_variance > 0.0


class TestVarianceReport:
    def test_total_variance(self) -> None:
        report = VarianceReport(run_variance=0.1, order_variance=0.2)
        assert report.total_variance > 0.0

    def test_total_variance_run_only(self) -> None:
        report = VarianceReport(run_variance=0.1)
        assert report.total_variance == pytest.approx(0.1)


class TestComputeRunVariance:
    def test_identical_runs(self) -> None:
        scores = [[0.5, 0.5], [0.5, 0.5]]
        assert compute_run_variance(scores) == 0.0

    def test_different_runs(self) -> None:
        scores = [[0.0, 0.0], [1.0, 1.0]]
        assert compute_run_variance(scores) > 0.0
