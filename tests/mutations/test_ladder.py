"""Tests for escalation ladder — tier tracking, escalation logic."""
from __future__ import annotations

import pytest

from prompter.mutations.ladder import ESCALATION_TIERS, LadderState, MAX_CONSECUTIVE_FAILURES_BEFORE_ESCALATE


class TestLadderState:
    def test_initial_state(self) -> None:
        ladder = LadderState()
        assert ladder.current_tier == 1
        assert ladder.get_allowed_types() == ["prompt.rewrite"]

    def test_record_success_resets_failures(self) -> None:
        ladder = LadderState()
        ladder.record_result(1, accepted=False)
        ladder.record_result(1, accepted=False)
        ladder.record_result(1, accepted=True)
        assert ladder.consecutive_failures[1] == 0

    def test_escalation_after_consecutive_failures(self) -> None:
        ladder = LadderState()
        for _ in range(MAX_CONSECUTIVE_FAILURES_BEFORE_ESCALATE):
            ladder.record_result(1, accepted=False)

        assert ladder.should_escalate(1) is True
        escalated = ladder.escalate()
        assert escalated is True
        assert ladder.current_tier == 2

    def test_no_escalation_before_threshold(self) -> None:
        ladder = LadderState()
        ladder.record_result(1, accepted=False)
        assert ladder.should_escalate(1) is False

    def test_escalate_adds_allowed_types(self) -> None:
        ladder = LadderState()
        ladder.current_tier = 2
        allowed = ladder.get_allowed_types()
        assert "prompt.rewrite" in allowed
        assert "tool_desc.edit" in allowed

    def test_escalate_at_max_returns_false(self) -> None:
        max_tier = max(t["tier"] for t in ESCALATION_TIERS)
        ladder = LadderState(current_tier=max_tier)
        assert ladder.escalate() is False

    def test_current_tier_label(self) -> None:
        ladder = LadderState()
        assert ladder.current_tier_label == "System prompt"

    def test_tier_label_unknown(self) -> None:
        ladder = LadderState(current_tier=999)
        assert "999" in ladder.current_tier_label
