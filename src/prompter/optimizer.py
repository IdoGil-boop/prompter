"""Optimizer — main optimization loop for agent config improvement."""
from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import TYPE_CHECKING

# Import mutation modules to populate the registry via @register_mutation decorators
import prompter.mutations.architecture  # noqa: F401
import prompter.mutations.config_value  # noqa: F401
import prompter.mutations.prompt  # noqa: F401
import prompter.mutations.tool_desc  # noqa: F401
import prompter.mutations.tool_impl  # noqa: F401
import prompter.mutations.tool_manage  # noqa: F401
from prompter.attribution.matrix import AttributionMatrix
from prompter.attribution.tracer import TraceAttributor
from prompter.config.snapshot import ConfigSnapshot
from prompter.eval.evaluator import EvalReport, Evaluator
from prompter.eval.variance import effective_score
from prompter.history.store import HistoryStore, IterationRecord
from prompter.llm.escalation import ModelEscalation
from prompter.mutations.base import Mutation, MutationContext
from prompter.mutations.ladder import LadderState
from prompter.mutations.proposer import MutationProposer
from prompter.runner.agent_runner import AgentRunner

if TYPE_CHECKING:
    from pathlib import Path

    from prompter.config.agent_config import AgentConfig
    from prompter.eval.test_suite import TestSuite
    from prompter.llm.adapter import LLMAdapter

logger = logging.getLogger(__name__)


VALID_VARIANCE_MODES = {"run", "order", "paraphrase"}


@dataclass(frozen=True)
class OptimizerConfig:
    """Configuration for the optimization loop."""

    max_iterations: int = 20
    target_score: float = 1.0
    n_eval_runs: int = 3
    compute_ci: bool = True
    variance_lambda: float = 0.1
    improvement_threshold: float = 0.01
    snapshots_dir: Path | None = None
    ablation_interval: int = 5
    enable_attribution: bool = True
    variance_modes: list[str] = None  # type: ignore[assignment]

    def __post_init__(self) -> None:
        if self.variance_modes is None:
            object.__setattr__(self, "variance_modes", ["run"])
        for mode in self.variance_modes:
            if mode not in VALID_VARIANCE_MODES:
                raise ValueError(
                    f"Invalid variance mode '{mode}'. "
                    f"Valid modes: {sorted(VALID_VARIANCE_MODES)}"
                )


@dataclass(frozen=True)
class OptimizationResult:
    """Result of an optimization run."""

    best_config: AgentConfig
    baseline_report: EvalReport
    final_report: EvalReport
    iterations_run: int
    history_path: Path | None = None


class Optimizer:
    """Runs the evaluate-mutate-evaluate loop to improve an agent config."""

    def __init__(
        self,
        config: AgentConfig,
        test_suite: TestSuite,
        llm: LLMAdapter,
        optimizer_llm: LLMAdapter | None = None,
        opt_config: OptimizerConfig | None = None,
        history_path: Path | None = None,
        escalation_tiers: dict[str, LLMAdapter] | None = None,
    ) -> None:
        self._config = config
        self._test_suite = test_suite
        self._llm = llm
        self._optimizer_llm = optimizer_llm or llm
        self._opt_config = opt_config or OptimizerConfig()
        self._history = HistoryStore(history_path) if history_path else None
        self._evaluator = Evaluator(
            n_runs=self._opt_config.n_eval_runs,
            compute_variance=self._opt_config.n_eval_runs > 1,
            compute_ci=(
                self._opt_config.compute_ci
                and self._opt_config.n_eval_runs > 1
            ),
        )
        self._proposer = MutationProposer(self._optimizer_llm)
        self._ladder = LadderState()
        self._trace_attributor = TraceAttributor()
        self._attribution_matrix = AttributionMatrix()

        # Model escalation setup
        self._escalation: ModelEscalation | None = None
        if escalation_tiers:
            self._escalation = ModelEscalation(
                tiers=escalation_tiers,
                improvement_threshold=self._opt_config.improvement_threshold,
            )

    async def run(self) -> OptimizationResult:
        """Main optimization loop."""
        current_config = self._config

        # Evaluate baseline
        initial_baseline_report = await self._evaluate(current_config)
        baseline_report = initial_baseline_report
        current_score = self._compute_effective_score(baseline_report)
        best_config = current_config
        best_score = current_score

        logger.info(
            "Baseline score: %.4f (%d/%d passed)",
            current_score,
            len(baseline_report.passed),
            len(baseline_report.results),
        )

        # Record baseline in history
        if self._history:
            self._history.append(IterationRecord(
                iteration=0,
                timestamp=datetime.now(UTC).isoformat(),
                config_hash=current_config.config_hash(),
                score_before=0.0,
                score_after=current_score,
                accepted=True,
                mutation_type=None,
                mutation_description="Baseline evaluation",
            ))

        # Save baseline snapshot
        if self._opt_config.snapshots_dir:
            self._opt_config.snapshots_dir.mkdir(parents=True, exist_ok=True)
            ConfigSnapshot.create(
                current_config, 0
            ).save(self._opt_config.snapshots_dir)

        iterations_run = 0

        for i in range(1, self._opt_config.max_iterations + 1):
            # Check if we hit target
            if current_score >= self._opt_config.target_score:
                logger.info(
                    "Target score %.4f reached at iteration %d",
                    current_score, i - 1,
                )
                break

            logger.info("=== Iteration %d ===", i)
            iterations_run = i

            # Run trace attribution on current evaluation results
            if self._opt_config.enable_attribution:
                self._update_trace_attribution(baseline_report)

            # Run ablation sweep periodically
            if (
                self._opt_config.enable_attribution
                and self._opt_config.ablation_interval > 0
                and i % self._opt_config.ablation_interval == 0
            ):
                await self._run_ablation_sweep(current_config)

            # Check stagnation and trigger escalation
            if self._history:
                from prompter.history.analysis import HistoryAnalyzer

                analyzer = HistoryAnalyzer(self._history)
                if analyzer.stagnation_detector(window=5):
                    logger.info(
                        "Stagnation detected — escalating mutation tier"
                    )
                    self._ladder.escalate()

            # Build mutation context
            history_for_proposer = (
                self._history.get_history_for_proposer()
                if self._history
                else []
            )
            attribution_hints = (
                self._attribution_matrix.as_hints()
                if self._opt_config.enable_attribution
                else {}
            )
            context = MutationContext(
                config=current_config,
                eval_report=baseline_report,
                history=history_for_proposer,
                attribution_hints=attribution_hints,
                test_suite=self._test_suite,
            )

            # Propose mutation
            try:
                proposal = await self._proposer.propose(
                    context, self._ladder
                )
            except Exception as exc:
                logger.warning("Proposer failed: %s", exc)
                continue

            logger.info(
                "Proposed: %s — %s",
                proposal.mutation_type,
                proposal.rationale[:100],
            )

            # Get mutation operator from registry and instantiate
            registry = Mutation.registry()
            mutation_cls = registry.get(proposal.mutation_type)
            if mutation_cls is None:
                logger.warning(
                    "No mutation registered for type: %s",
                    proposal.mutation_type,
                )
                continue

            # Registry stores concrete subclasses that take llm in __init__
            mutation = mutation_cls(self._optimizer_llm)  # type: ignore[call-arg]

            # Apply mutation
            try:
                mutation_result = await mutation.apply(context, proposal)
            except Exception as exc:
                logger.warning("Mutation apply failed: %s", exc)
                continue

            # Evaluate candidate
            candidate_report = await self._evaluate(mutation_result.config)
            candidate_score = self._compute_effective_score(candidate_report)
            delta = candidate_score - current_score

            logger.info(
                "Score: %.4f -> %.4f (delta: %+.4f)",
                current_score, candidate_score, delta,
            )

            # Escalation validation (if configured)
            escalation_rejected = False
            if self._escalation and delta >= self._opt_config.improvement_threshold:
                candidate_config = mutation_result.config
                escalation_result = await self._escalation.validate(
                    eval_fn=lambda adapter, cfg=candidate_config: self._evaluate_with(
                        cfg, adapter
                    ),
                    baseline_score=current_score,
                )
                if not escalation_result.accepted:
                    logger.info(
                        "Escalation rejected mutation at tier '%s': %s",
                        escalation_result.rejection_tier,
                        escalation_result.rejection_reason,
                    )
                    escalation_rejected = True

            # Decide accept/reject
            accepted = (
                delta >= self._opt_config.improvement_threshold
                and not escalation_rejected
            )
            tier = proposal.cost_tier

            if accepted:
                current_config = mutation_result.config
                current_score = candidate_score
                baseline_report = candidate_report
                self._ladder.record_result(tier, accepted=True)
                logger.info("ACCEPTED mutation")

                if candidate_score > best_score:
                    best_config = current_config
                    best_score = candidate_score
            else:
                self._ladder.record_result(tier, accepted=False)
                if self._ladder.should_escalate(tier):
                    self._ladder.escalate()
                logger.info(
                    "REJECTED mutation (delta %.4f < threshold %.4f)",
                    delta, self._opt_config.improvement_threshold,
                )

            # Record in history
            if self._history:
                self._history.append(IterationRecord(
                    iteration=i,
                    timestamp=datetime.now(UTC).isoformat(),
                    config_hash=mutation_result.config.config_hash(),
                    mutation_type=proposal.mutation_type,
                    mutation_description=mutation_result.description,
                    components_touched=mutation_result.components_touched,
                    score_before=(
                        current_score
                        if not accepted
                        else current_score - delta
                    ),
                    score_after=candidate_score,
                    accepted=accepted,
                    rejection_reason=(
                        None
                        if accepted
                        else f"delta {delta:.4f} < threshold"
                    ),
                ))

            # Save snapshot
            if self._opt_config.snapshots_dir:
                ConfigSnapshot.create(
                    mutation_result.config if accepted else current_config, i
                ).save(self._opt_config.snapshots_dir)

        # Final evaluation of best config
        final_report = await self._evaluate(best_config)

        return OptimizationResult(
            best_config=best_config,
            baseline_report=initial_baseline_report,
            final_report=final_report,
            iterations_run=iterations_run,
            history_path=self._history.path if self._history else None,
        )

    async def _evaluate(self, config: AgentConfig) -> EvalReport:
        """Create a fresh AgentRunner and evaluate it."""
        runner = AgentRunner(config=config, llm=self._llm)
        agent_fn = runner.as_agent_fn()
        return await self._evaluator.evaluate(
            agent_fn=agent_fn,
            test_suite=self._test_suite,
            config_id=config.config_hash(),
        )

    async def _evaluate_with(self, config: AgentConfig, adapter: LLMAdapter) -> float:
        """Evaluate a config with a specific LLM adapter. Returns the score."""
        runner = AgentRunner(config=config, llm=adapter)
        agent_fn = runner.as_agent_fn()
        report = await self._evaluator.evaluate(
            agent_fn=agent_fn,
            test_suite=self._test_suite,
            config_id=config.config_hash(),
        )
        return self._compute_effective_score(report)

    def _compute_effective_score(self, report: EvalReport) -> float:
        """Compute effective score, penalizing variance if available."""
        if (
            report.variance_report is not None
            and self._opt_config.variance_lambda > 0
        ):
            return effective_score(
                report.aggregate_score,
                report.variance_report.total_variance,
                self._opt_config.variance_lambda,
            )
        return report.aggregate_score

    def _update_trace_attribution(self, report: EvalReport) -> None:
        """Run trace attribution on evaluation results and merge into matrix."""
        for result in report.results:
            if result.trace:
                attr = self._trace_attributor.attribute(result.trace, result)
                self._attribution_matrix.merge_trace(attr, test_id=result.test_id)

    async def _run_ablation_sweep(self, config: AgentConfig) -> None:
        """Run ablation sweep and merge results into attribution matrix."""
        from prompter.attribution.ablation import AblationSweep

        logger.info("Running ablation sweep...")
        sweep = AblationSweep()
        try:
            result = await sweep.run(
                config, self._test_suite, self._evaluator, self._llm
            )
            self._attribution_matrix.merge_ablation(result)
            logger.info(
                "Ablation sweep complete. Top suspects: %s",
                self._attribution_matrix.top_suspects(3),
            )
        except Exception as exc:
            logger.warning("Ablation sweep failed: %s", exc)
