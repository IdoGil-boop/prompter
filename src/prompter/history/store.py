from __future__ import annotations

import json
import logging
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class IterationRecord:
    iteration: int
    timestamp: str
    config_hash: str
    mutation_type: str | None = None
    mutation_description: str | None = None
    components_touched: list[str] = field(default_factory=list)
    score_before: float = 0.0
    score_after: float = 0.0
    accepted: bool = False
    rejection_reason: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def delta(self) -> float:
        return self.score_after - self.score_before

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> IterationRecord:
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})


class HistoryStore:
    """Append-only JSONL store for optimization history."""

    def __init__(self, path: Path | str):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._records: list[IterationRecord] = []
        if self.path.exists():
            self._load()

    def append(self, record: IterationRecord) -> None:
        self._records.append(record)
        with open(self.path, "a", encoding="utf-8") as f:
            f.write(json.dumps(record.to_dict()) + "\n")

    def get_all(self) -> list[IterationRecord]:
        return list(self._records)

    def get_best(self) -> IterationRecord | None:
        accepted = [r for r in self._records if r.accepted]
        if not accepted:
            return self._records[0] if self._records else None
        return max(accepted, key=lambda r: r.score_after)

    def get_history_for_proposer(self) -> list[dict[str, Any]]:
        """Compact history suitable for the mutation proposer prompt."""
        return [
            {
                "iteration": r.iteration,
                "mutation_type": r.mutation_type,
                "description": r.mutation_description,
                "accepted": r.accepted,
                "delta": r.delta,
            }
            for r in self._records
            if r.mutation_type is not None
        ]

    @property
    def best_score(self) -> float:
        if not self._records:
            return 0.0
        accepted = [r for r in self._records if r.accepted]
        if accepted:
            return max(r.score_after for r in accepted)
        return self._records[0].score_after if self._records else 0.0

    def _load(self) -> None:
        with open(self.path, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    self._records.append(IterationRecord.from_dict(json.loads(line)))
        logger.info("Loaded %d iteration records from %s", len(self._records), self.path)
