"""HistoryAnalyzer — extracts patterns from optimization history."""
from __future__ import annotations

import logging
from collections import Counter, defaultdict
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from prompter.history.store import HistoryStore

logger = logging.getLogger(__name__)


class HistoryAnalyzer:
    """Extracts patterns from optimization history for insights."""

    def __init__(self, store: HistoryStore) -> None:
        self._store = store

    def stagnation_detector(self, window: int = 5) -> bool:
        """True if score hasn't improved in last K iterations.

        Looks at the last `window` records (excluding baseline).
        If none were accepted, we're stagnating.
        """
        records = self._store.get_all()
        # Filter to mutation records (exclude baseline with no mutation_type)
        mutation_records = [r for r in records if r.mutation_type is not None]

        if len(mutation_records) < window:
            return False

        recent = mutation_records[-window:]
        return not any(r.accepted for r in recent)

    def mutation_effectiveness(self) -> dict[str, float]:
        """Acceptance rate per mutation type.

        Returns dict mapping mutation_type -> acceptance_rate (0.0 to 1.0).
        Only includes records with a mutation_type.
        """
        records = self._store.get_all()
        type_counts: dict[str, int] = defaultdict(int)
        type_accepted: dict[str, int] = defaultdict(int)

        for r in records:
            if r.mutation_type is None:
                continue
            type_counts[r.mutation_type] += 1
            if r.accepted:
                type_accepted[r.mutation_type] += 1

        return {
            mt: type_accepted[mt] / count
            for mt, count in type_counts.items()
            if count > 0
        }

    def component_churn(self) -> dict[str, int]:
        """How many times each component has been mutated.

        Counts components_touched across all records.
        """
        records = self._store.get_all()
        churn: Counter[str] = Counter()
        for r in records:
            for component in r.components_touched:
                churn[component] += 1
        return dict(churn)

    def summary(self) -> str:
        """Human-readable optimization summary."""
        records = self._store.get_all()
        if not records:
            return "No optimization history."

        total = len(records)
        mutation_records = [r for r in records if r.mutation_type is not None]
        accepted = [r for r in mutation_records if r.accepted]
        best_score = max((r.score_after for r in records), default=0.0)
        first_score = records[0].score_after if records else 0.0

        lines = [
            f"Optimization summary: {total} iterations",
            f"  Score: {first_score:.4f} -> {best_score:.4f}",
            f"  Mutations tried: {len(mutation_records)}",
            f"  Mutations accepted: {len(accepted)}",
        ]

        effectiveness = self.mutation_effectiveness()
        if effectiveness:
            lines.append("  Effectiveness by type:")
            for mt, rate in sorted(effectiveness.items()):
                lines.append(f"    {mt}: {rate:.1%}")

        churn = self.component_churn()
        if churn:
            lines.append("  Component churn:")
            for comp, count in sorted(churn.items(), key=lambda x: -x[1]):
                lines.append(f"    {comp}: {count} mutations")

        return "\n".join(lines)
