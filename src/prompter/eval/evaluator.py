from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any, Protocol

from prompter.eval.bootstrap import BootstrapResult, bootstrap_ci
from prompter.eval.metrics import score_output
from prompter.eval.variance import VarianceReport, VarianceTracker

if TYPE_CHECKING:
    from prompter.eval.test_suite import TestCase, TestSuite

logger = logging.getLogger(__name__)


class AgentFn(Protocol):
    async def __call__(
        self, input_text: str, context: dict[str, Any] | None = None
    ) -> str: ...


@dataclass(frozen=True)
class TraceEvent:
    timestamp: float
    event_type: str
    component: str
    data: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class TestResult:
    test_id: str
    score: float
    actual_output: str
    trace: list[TraceEvent] = field(default_factory=list)
    latency_ms: float = 0.0
    error: str | None = None


@dataclass(frozen=True)
class EvalReport:
    config_id: str
    aggregate_score: float
    results: list[TestResult]
    confidence_interval: BootstrapResult | None = None
    variance_report: VarianceReport | None = None
    total_latency_ms: float = 0.0

    @property
    def passed(self) -> list[TestResult]:
        return [r for r in self.results if r.score >= 1.0]

    @property
    def failed(self) -> list[TestResult]:
        return [r for r in self.results if r.score < 1.0]

    @property
    def pass_rate(self) -> float:
        if not self.results:
            return 0.0
        return len(self.passed) / len(self.results)


class Evaluator:
    """Runs an agent config against a test suite and produces an EvalReport."""

    def __init__(
        self,
        n_runs: int = 1,
        compute_variance: bool = False,
        compute_ci: bool = False,
    ):
        self.n_runs = n_runs
        self.compute_variance = compute_variance
        self.compute_ci = compute_ci

    async def evaluate(
        self,
        agent_fn: AgentFn,
        test_suite: TestSuite,
        config_id: str = "",
    ) -> EvalReport:
        """
        Run all test cases through agent_fn, optionally multiple times.

        agent_fn: async callable (input: str, context: dict | None) -> str
        """
        start = time.monotonic()
        variance_tracker = VarianceTracker() if self.compute_variance else None
        all_run_results: list[list[TestResult]] = []

        for _run_idx in range(self.n_runs):
            run_results = []
            for test in test_suite.tests:
                result = await self._run_single(agent_fn, test)
                run_results.append(result)
            all_run_results.append(run_results)

            if variance_tracker:
                variance_tracker.add_run([r.score for r in run_results])

        best_results = all_run_results[0]

        weighted_sum = sum(
            r.score * t.weight
            for r, t in zip(best_results, test_suite.tests, strict=True)
        )
        total_weight = test_suite.total_weight
        aggregate = weighted_sum / total_weight if total_weight > 0 else 0.0

        ci = None
        if self.compute_ci and self.n_runs > 1:
            all_agg_scores = []
            for run in all_run_results:
                ws = sum(
                    r.score * t.weight
                    for r, t in zip(run, test_suite.tests, strict=True)
                )
                all_agg_scores.append(ws / total_weight)
            ci = bootstrap_ci(all_agg_scores)

        variance_report = variance_tracker.report() if variance_tracker else None
        total_latency = (time.monotonic() - start) * 1000

        return EvalReport(
            config_id=config_id,
            aggregate_score=aggregate,
            results=best_results,
            confidence_interval=ci,
            variance_report=variance_report,
            total_latency_ms=total_latency,
        )

    async def _run_single(self, agent_fn: AgentFn, test: TestCase) -> TestResult:
        start = time.monotonic()
        try:
            actual = await agent_fn(test.input, test.context)
            score = score_output(actual, test.expected, test.eval_mode, test.eval_config)
            latency = (time.monotonic() - start) * 1000
            return TestResult(
                test_id=test.id,
                score=score,
                actual_output=actual,
                latency_ms=latency,
            )
        except Exception as e:
            latency = (time.monotonic() - start) * 1000
            logger.warning("Test %s failed with error: %s", test.id, e)
            return TestResult(
                test_id=test.id,
                score=0.0,
                actual_output="",
                latency_ms=latency,
                error=str(e),
            )
