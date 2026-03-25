from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import TYPE_CHECKING, Protocol

if TYPE_CHECKING:
    from prompter.llm.adapter import LLMAdapter

logger = logging.getLogger(__name__)

TIER_ORDER: list[str] = ["local", "cheap", "sota"]


@dataclass(frozen=True)
class EscalationResult:
    accepted: bool
    tier_reached: str
    scores_by_tier: dict[str, float]
    rejection_tier: str | None = None
    rejection_reason: str | None = None


class ModelEscalation:
    """Validates mutations across model tiers with early exit on failure."""

    def __init__(
        self,
        tiers: dict[str, LLMAdapter],
        regression_threshold: float = -0.02,
        improvement_threshold: float = 0.01,
    ):
        self.tiers = tiers
        self.regression_threshold = regression_threshold
        self.improvement_threshold = improvement_threshold
        self._available_tiers = [t for t in TIER_ORDER if t in tiers]

        if not self._available_tiers:
            raise ValueError("At least one model tier must be provided")

    async def validate(
        self,
        eval_fn: EscalationEvalFn,
        baseline_score: float,
    ) -> EscalationResult:
        """
        Run eval_fn at each tier. Short-circuit if regression detected.

        eval_fn: async callable(adapter: LLMAdapter) -> float (score)
        """
        scores: dict[str, float] = {}

        for tier_name in self._available_tiers:
            adapter = self.tiers[tier_name]
            logger.info("Evaluating at tier '%s' (model: %s)", tier_name, adapter.model_id)

            score = await eval_fn(adapter)
            scores[tier_name] = score
            delta = score - baseline_score

            if delta < self.regression_threshold:
                logger.info(
                    "Rejected at tier '%s': score %.4f (delta %.4f < threshold %.4f)",
                    tier_name, score, delta, self.regression_threshold,
                )
                return EscalationResult(
                    accepted=False,
                    tier_reached=tier_name,
                    scores_by_tier=scores,
                    rejection_tier=tier_name,
                    rejection_reason=f"Regression at {tier_name}: {delta:.4f}",
                )

            logger.info(
                "Passed tier '%s': score %.4f (delta %.4f)",
                tier_name, score, delta,
            )

        final_tier = self._available_tiers[-1]
        final_delta = scores[final_tier] - baseline_score
        accepted = final_delta >= self.improvement_threshold

        if not accepted:
            return EscalationResult(
                accepted=False,
                tier_reached=final_tier,
                scores_by_tier=scores,
                rejection_tier=final_tier,
                rejection_reason=f"Insufficient improvement: {final_delta:.4f}",
            )

        return EscalationResult(
            accepted=True,
            tier_reached=final_tier,
            scores_by_tier=scores,
        )


class EscalationEvalFn(Protocol):
    async def __call__(self, adapter: LLMAdapter) -> float: ...
