"""Tests for HistoryAnalyzer — analysis over optimization history."""
from __future__ import annotations

import tempfile
from pathlib import Path

from prompter.history.analysis import HistoryAnalyzer
from prompter.history.store import HistoryStore, IterationRecord


def _make_store(records: list[IterationRecord]) -> HistoryStore:
    """Helper: create a HistoryStore with given records."""
    with tempfile.NamedTemporaryFile(suffix=".jsonl", delete=False) as f:
        path = Path(f.name)
    store = HistoryStore(path)
    for r in records:
        store.append(r)
    return store


class TestStagnationDetector:
    def test_no_stagnation_with_improvement(self) -> None:
        records = [
            IterationRecord(
                iteration=0, timestamp="t", config_hash="h",
                score_after=0.3, accepted=True,
            ),
            IterationRecord(
                iteration=1, timestamp="t", config_hash="h",
                mutation_type="prompt.rewrite",
                score_before=0.3, score_after=0.5, accepted=True,
            ),
            IterationRecord(
                iteration=2, timestamp="t", config_hash="h",
                mutation_type="prompt.rewrite",
                score_before=0.5, score_after=0.7, accepted=True,
            ),
        ]
        store = _make_store(records)
        analyzer = HistoryAnalyzer(store)
        assert analyzer.stagnation_detector(window=3) is False

    def test_stagnation_detected(self) -> None:
        records = [
            IterationRecord(
                iteration=0, timestamp="t", config_hash="h",
                score_after=0.5, accepted=True,
            ),
            IterationRecord(
                iteration=1, timestamp="t", config_hash="h",
                mutation_type="prompt.rewrite",
                score_before=0.5, score_after=0.5, accepted=False,
            ),
            IterationRecord(
                iteration=2, timestamp="t", config_hash="h",
                mutation_type="prompt.rewrite",
                score_before=0.5, score_after=0.5, accepted=False,
            ),
            IterationRecord(
                iteration=3, timestamp="t", config_hash="h",
                mutation_type="tool_desc.edit",
                score_before=0.5, score_after=0.49, accepted=False,
            ),
            IterationRecord(
                iteration=4, timestamp="t", config_hash="h",
                mutation_type="tool_desc.edit",
                score_before=0.5, score_after=0.5, accepted=False,
            ),
            IterationRecord(
                iteration=5, timestamp="t", config_hash="h",
                mutation_type="config.adjust",
                score_before=0.5, score_after=0.51, accepted=False,
            ),
        ]
        store = _make_store(records)
        analyzer = HistoryAnalyzer(store)
        assert analyzer.stagnation_detector(window=5) is True

    def test_stagnation_empty_history(self) -> None:
        store = _make_store([])
        analyzer = HistoryAnalyzer(store)
        assert analyzer.stagnation_detector(window=5) is False


class TestMutationEffectiveness:
    def test_effectiveness_rates(self) -> None:
        records = [
            IterationRecord(
                iteration=0, timestamp="t", config_hash="h",
                score_after=0.3, accepted=True,
            ),
            IterationRecord(
                iteration=1, timestamp="t", config_hash="h",
                mutation_type="prompt.rewrite",
                score_after=0.5, accepted=True,
            ),
            IterationRecord(
                iteration=2, timestamp="t", config_hash="h",
                mutation_type="prompt.rewrite",
                score_after=0.4, accepted=False,
            ),
            IterationRecord(
                iteration=3, timestamp="t", config_hash="h",
                mutation_type="tool_desc.edit",
                score_after=0.6, accepted=True,
            ),
            IterationRecord(
                iteration=4, timestamp="t", config_hash="h",
                mutation_type="tool_desc.edit",
                score_after=0.5, accepted=False,
            ),
            IterationRecord(
                iteration=5, timestamp="t", config_hash="h",
                mutation_type="tool_desc.edit",
                score_after=0.4, accepted=False,
            ),
        ]
        store = _make_store(records)
        analyzer = HistoryAnalyzer(store)
        effectiveness = analyzer.mutation_effectiveness()
        # prompt.rewrite: 1/2 = 0.5
        assert effectiveness["prompt.rewrite"] == 0.5
        # tool_desc.edit: 1/3 ~= 0.333
        assert abs(effectiveness["tool_desc.edit"] - 1 / 3) < 0.01

    def test_effectiveness_empty_history(self) -> None:
        store = _make_store([])
        analyzer = HistoryAnalyzer(store)
        assert analyzer.mutation_effectiveness() == {}


class TestComponentChurn:
    def test_churn_counts(self) -> None:
        records = [
            IterationRecord(
                iteration=0, timestamp="t", config_hash="h",
                score_after=0.3, accepted=True,
            ),
            IterationRecord(
                iteration=1, timestamp="t", config_hash="h",
                mutation_type="prompt.rewrite",
                components_touched=["system_prompt"], accepted=True,
            ),
            IterationRecord(
                iteration=2, timestamp="t", config_hash="h",
                mutation_type="prompt.rewrite",
                components_touched=["system_prompt"], accepted=True,
            ),
            IterationRecord(
                iteration=3, timestamp="t", config_hash="h",
                mutation_type="tool_desc.edit",
                components_touched=["tool:search"], accepted=True,
            ),
        ]
        store = _make_store(records)
        analyzer = HistoryAnalyzer(store)
        churn = analyzer.component_churn()
        assert churn["system_prompt"] == 2
        assert churn["tool:search"] == 1

    def test_churn_empty(self) -> None:
        store = _make_store([])
        analyzer = HistoryAnalyzer(store)
        assert analyzer.component_churn() == {}


class TestSummary:
    def test_summary_returns_string(self) -> None:
        records = [
            IterationRecord(
                iteration=0, timestamp="t", config_hash="h",
                score_after=0.3, accepted=True,
            ),
            IterationRecord(
                iteration=1, timestamp="t", config_hash="h",
                mutation_type="prompt.rewrite",
                score_before=0.3, score_after=0.6, accepted=True,
            ),
        ]
        store = _make_store(records)
        analyzer = HistoryAnalyzer(store)
        s = analyzer.summary()
        assert isinstance(s, str)
        assert len(s) > 0
        # Should mention the score
        assert "0.6" in s or "0.3" in s

    def test_summary_empty(self) -> None:
        store = _make_store([])
        analyzer = HistoryAnalyzer(store)
        s = analyzer.summary()
        assert isinstance(s, str)
