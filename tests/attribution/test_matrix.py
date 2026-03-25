"""Tests for AttributionMatrix — combines trace and ablation attribution."""
from __future__ import annotations

from prompter.attribution.ablation import AblationResult
from prompter.attribution.matrix import AttributionMatrix
from prompter.attribution.tracer import TraceAttribution


class TestAttributionMatrix:
    def test_empty_matrix(self) -> None:
        matrix = AttributionMatrix()
        assert matrix.matrix == {}
        assert matrix.top_suspects(3) == []

    def test_merge_trace(self) -> None:
        matrix = AttributionMatrix()
        trace_attr = TraceAttribution(
            component_scores={"system_prompt": 0.8, "tool:search": 0.3}
        )
        matrix.merge_trace(trace_attr, test_id="t1")
        assert matrix.matrix["system_prompt"]["t1"] == 0.8
        assert matrix.matrix["tool:search"]["t1"] == 0.3

    def test_merge_multiple_traces(self) -> None:
        matrix = AttributionMatrix()
        matrix.merge_trace(
            TraceAttribution(component_scores={"system_prompt": 0.5}),
            test_id="t1",
        )
        matrix.merge_trace(
            TraceAttribution(component_scores={"system_prompt": 0.9}),
            test_id="t2",
        )
        assert matrix.matrix["system_prompt"]["t1"] == 0.5
        assert matrix.matrix["system_prompt"]["t2"] == 0.9

    def test_merge_ablation(self) -> None:
        matrix = AttributionMatrix()
        ablation = AblationResult(
            component_deltas={"system_prompt": 0.6, "tool:calc": -0.2},
            baseline_score=0.8,
        )
        matrix.merge_ablation(ablation)
        # Ablation merges under a special "_ablation" test_id key
        assert matrix.matrix["system_prompt"]["_ablation"] == 0.6
        assert matrix.matrix["tool:calc"]["_ablation"] == -0.2

    def test_top_suspects(self) -> None:
        matrix = AttributionMatrix()
        # system_prompt has high trace scores
        matrix.merge_trace(
            TraceAttribution(component_scores={"system_prompt": 0.9, "tool:a": 0.1}),
            test_id="t1",
        )
        matrix.merge_trace(
            TraceAttribution(component_scores={"system_prompt": 0.8, "tool:a": 0.2}),
            test_id="t2",
        )
        suspects = matrix.top_suspects(1)
        assert suspects == ["system_prompt"]

    def test_top_suspects_limit(self) -> None:
        matrix = AttributionMatrix()
        matrix.merge_trace(
            TraceAttribution(
                component_scores={"a": 0.9, "b": 0.5, "c": 0.3, "d": 0.1}
            ),
            test_id="t1",
        )
        assert len(matrix.top_suspects(2)) == 2
        assert matrix.top_suspects(2) == ["a", "b"]

    def test_top_suspects_includes_ablation(self) -> None:
        """Ablation data contributes to suspect ranking."""
        matrix = AttributionMatrix()
        # trace says tool:a is minor
        matrix.merge_trace(
            TraceAttribution(component_scores={"tool:a": 0.1, "tool:b": 0.2}),
            test_id="t1",
        )
        # But ablation says tool:a has huge impact
        matrix.merge_ablation(
            AblationResult(
                component_deltas={"tool:a": 0.9, "tool:b": 0.05},
                baseline_score=0.8,
            )
        )
        suspects = matrix.top_suspects(1)
        assert suspects == ["tool:a"]

    def test_as_hints(self) -> None:
        """Convert matrix to flat dict for MutationContext.attribution_hints."""
        matrix = AttributionMatrix()
        matrix.merge_trace(
            TraceAttribution(component_scores={"system_prompt": 0.7, "tool:x": 0.3}),
            test_id="t1",
        )
        hints = matrix.as_hints()
        assert isinstance(hints, dict)
        assert "system_prompt" in hints
        assert "tool:x" in hints
