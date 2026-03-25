"""Tests for HistoryStore — append/load/get_best/JSONL round-trip."""
from __future__ import annotations

import tempfile
from pathlib import Path

import pytest

from prompter.history.store import HistoryStore, IterationRecord


class TestIterationRecord:
    def test_delta_property(self) -> None:
        record = IterationRecord(
            iteration=1,
            timestamp="2026-01-01T00:00:00Z",
            config_hash="abc",
            score_before=0.5,
            score_after=0.8,
        )
        assert record.delta == pytest.approx(0.3)

    def test_to_dict_round_trip(self) -> None:
        record = IterationRecord(
            iteration=1,
            timestamp="2026-01-01T00:00:00Z",
            config_hash="abc",
            mutation_type="prompt.rewrite",
            mutation_description="Test mutation",
            score_before=0.5,
            score_after=0.8,
            accepted=True,
        )
        d = record.to_dict()
        loaded = IterationRecord.from_dict(d)
        assert loaded.iteration == 1
        assert loaded.mutation_type == "prompt.rewrite"
        assert loaded.accepted is True
        assert loaded.delta == pytest.approx(0.3)


class TestHistoryStore:
    def test_append_and_get_all(self) -> None:
        with tempfile.NamedTemporaryFile(suffix=".jsonl", delete=False) as f:
            path = Path(f.name)

        store = HistoryStore(path)
        record = IterationRecord(
            iteration=0,
            timestamp="2026-01-01T00:00:00Z",
            config_hash="abc",
            score_after=0.5,
            accepted=True,
        )
        store.append(record)

        records = store.get_all()
        assert len(records) == 1
        assert records[0].score_after == 0.5
        path.unlink()

    def test_persist_and_reload(self) -> None:
        with tempfile.NamedTemporaryFile(suffix=".jsonl", delete=False) as f:
            path = Path(f.name)

        store = HistoryStore(path)
        store.append(IterationRecord(
            iteration=0, timestamp="t", config_hash="a",
            score_after=0.5, accepted=True,
        ))
        store.append(IterationRecord(
            iteration=1, timestamp="t", config_hash="b",
            mutation_type="prompt.rewrite", score_before=0.5,
            score_after=0.8, accepted=True,
        ))

        # Reload from file
        store2 = HistoryStore(path)
        records = store2.get_all()
        assert len(records) == 2
        assert records[1].score_after == 0.8
        path.unlink()

    def test_get_best(self) -> None:
        with tempfile.NamedTemporaryFile(suffix=".jsonl", delete=False) as f:
            path = Path(f.name)

        store = HistoryStore(path)
        store.append(IterationRecord(
            iteration=0, timestamp="t", config_hash="a",
            score_after=0.5, accepted=True,
        ))
        store.append(IterationRecord(
            iteration=1, timestamp="t", config_hash="b",
            score_before=0.5, score_after=0.9, accepted=True,
        ))
        store.append(IterationRecord(
            iteration=2, timestamp="t", config_hash="c",
            score_before=0.9, score_after=0.7, accepted=False,
        ))

        best = store.get_best()
        assert best is not None
        assert best.score_after == 0.9
        path.unlink()

    def test_get_best_no_accepted(self) -> None:
        """If no accepted records, return first."""
        with tempfile.NamedTemporaryFile(suffix=".jsonl", delete=False) as f:
            path = Path(f.name)

        store = HistoryStore(path)
        store.append(IterationRecord(
            iteration=0, timestamp="t", config_hash="a",
            score_after=0.3, accepted=False,
        ))
        best = store.get_best()
        assert best is not None
        assert best.score_after == 0.3
        path.unlink()

    def test_get_best_empty(self) -> None:
        with tempfile.NamedTemporaryFile(suffix=".jsonl", delete=False) as f:
            path = Path(f.name)

        store = HistoryStore(path)
        assert store.get_best() is None
        path.unlink()

    def test_best_score_property(self) -> None:
        with tempfile.NamedTemporaryFile(suffix=".jsonl", delete=False) as f:
            path = Path(f.name)

        store = HistoryStore(path)
        store.append(IterationRecord(
            iteration=0, timestamp="t", config_hash="a",
            score_after=0.5, accepted=True,
        ))
        store.append(IterationRecord(
            iteration=1, timestamp="t", config_hash="b",
            score_after=0.8, accepted=True,
        ))
        assert store.best_score == 0.8
        path.unlink()

    def test_get_history_for_proposer(self) -> None:
        with tempfile.NamedTemporaryFile(suffix=".jsonl", delete=False) as f:
            path = Path(f.name)

        store = HistoryStore(path)
        store.append(IterationRecord(
            iteration=0, timestamp="t", config_hash="a",
            score_after=0.5, accepted=True,
        ))
        store.append(IterationRecord(
            iteration=1, timestamp="t", config_hash="b",
            mutation_type="prompt.rewrite",
            mutation_description="Rewrote prompt",
            score_before=0.5, score_after=0.7,
            accepted=True,
        ))

        history = store.get_history_for_proposer()
        # Baseline (no mutation_type) should be excluded
        assert len(history) == 1
        assert history[0]["mutation_type"] == "prompt.rewrite"
        path.unlink()
