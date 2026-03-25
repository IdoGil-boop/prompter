from __future__ import annotations

import logging
from collections import Counter
from dataclasses import dataclass
from typing import TypedDict

logger = logging.getLogger(__name__)


class TierInfo(TypedDict):
    tier: int
    types: list[str]
    label: str


ESCALATION_TIERS: list[TierInfo] = [
    {"tier": 1, "types": ["prompt.rewrite"], "label": "System prompt"},
    {"tier": 2, "types": ["tool_desc.edit"], "label": "Tool descriptions"},
    {"tier": 3, "types": ["config.adjust"], "label": "Config values"},
    {"tier": 4, "types": ["tool_impl.modify"], "label": "Tool implementation"},
    {"tier": 5, "types": ["tool.add", "tool.remove"], "label": "Add/remove tools"},
    {
        "tier": 6,
        "types": ["architecture.rag", "architecture.context", "architecture.memory"],
        "label": "Architecture changes",
    },
]

MAX_CONSECUTIVE_FAILURES_BEFORE_ESCALATE = 3


@dataclass
class LadderState:
    current_tier: int = 1
    consecutive_failures: dict[int, int] = None  # type: ignore[assignment]

    def __post_init__(self) -> None:
        if self.consecutive_failures is None:
            self.consecutive_failures = Counter()

    def record_result(self, tier: int, accepted: bool) -> None:
        if accepted:
            self.consecutive_failures[tier] = 0
        else:
            self.consecutive_failures[tier] = self.consecutive_failures.get(tier, 0) + 1

    def should_escalate(self, tier: int) -> bool:
        return self.consecutive_failures.get(tier, 0) >= MAX_CONSECUTIVE_FAILURES_BEFORE_ESCALATE

    def get_allowed_types(self) -> list[str]:
        allowed: list[str] = []
        for tier_info in ESCALATION_TIERS:
            if tier_info["tier"] <= self.current_tier:
                allowed.extend(tier_info["types"])
        return allowed

    def escalate(self) -> bool:
        """Move to next tier. Returns False if already at max."""
        max_tier = max(t["tier"] for t in ESCALATION_TIERS)
        if self.current_tier >= max_tier:
            return False
        self.current_tier += 1
        logger.info(
            "Escalated to tier %d: %s",
            self.current_tier,
            self.current_tier_label,
        )
        return True

    @property
    def current_tier_label(self) -> str:
        for t in ESCALATION_TIERS:
            if t["tier"] == self.current_tier:
                return t["label"]
        return f"Tier {self.current_tier}"
