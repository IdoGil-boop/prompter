"""Tests for TraceAttributor — trace-based component attribution."""
from __future__ import annotations

from prompter.attribution.tracer import TraceAttribution, TraceAttributor
from prompter.eval.evaluator import TestResult, TraceEvent


class TestTraceAttribution:
    def test_frozen_dataclass(self) -> None:
        attr = TraceAttribution(component_scores={"system_prompt": 0.8})
        assert attr.component_scores == {"system_prompt": 0.8}

    def test_immutable(self) -> None:
        attr = TraceAttribution(component_scores={"x": 1.0})
        try:
            attr.component_scores = {}  # type: ignore[misc]
            raise AssertionError("Should be frozen")
        except AttributeError:
            pass


class TestTraceAttributor:
    def test_attribute_single_failing_component(self) -> None:
        """A component appearing in failing traces gets high attribution."""
        attributor = TraceAttributor()
        trace = [
            TraceEvent(timestamp=1.0, event_type="llm_call", component="system_prompt"),
            TraceEvent(timestamp=2.0, event_type="tool_call", component="tool:search"),
        ]
        result = TestResult(
            test_id="t1", score=0.0, actual_output="wrong", trace=trace
        )
        attr = attributor.attribute(trace, result)
        assert "system_prompt" in attr.component_scores
        assert "tool:search" in attr.component_scores
        # Both components active in a failure => both get positive scores
        assert attr.component_scores["system_prompt"] > 0
        assert attr.component_scores["tool:search"] > 0

    def test_attribute_passing_test(self) -> None:
        """Components in passing tests get zero or low attribution."""
        attributor = TraceAttributor()
        trace = [
            TraceEvent(timestamp=1.0, event_type="llm_call", component="system_prompt"),
        ]
        result = TestResult(
            test_id="t1", score=1.0, actual_output="correct", trace=trace
        )
        attr = attributor.attribute(trace, result)
        # Passing test: components get 0 attribution (not suspects)
        assert attr.component_scores.get("system_prompt", 0.0) == 0.0

    def test_attribute_empty_trace(self) -> None:
        """Empty trace produces empty attribution."""
        attributor = TraceAttributor()
        result = TestResult(test_id="t1", score=0.0, actual_output="")
        attr = attributor.attribute([], result)
        assert attr.component_scores == {}

    def test_attribute_partial_score(self) -> None:
        """Partial scores produce proportional attribution."""
        attributor = TraceAttributor()
        trace = [
            TraceEvent(timestamp=1.0, event_type="llm_call", component="system_prompt"),
        ]
        result = TestResult(
            test_id="t1", score=0.5, actual_output="partial", trace=trace
        )
        attr = attributor.attribute(trace, result)
        # Partial failure => some attribution
        assert attr.component_scores["system_prompt"] > 0
        assert attr.component_scores["system_prompt"] < 1.0

    def test_attribute_multiple_components(self) -> None:
        """Multiple components each get attribution proportional to involvement."""
        attributor = TraceAttributor()
        trace = [
            TraceEvent(timestamp=1.0, event_type="llm_call", component="system_prompt"),
            TraceEvent(timestamp=2.0, event_type="tool_call", component="tool:search"),
            TraceEvent(timestamp=3.0, event_type="tool_call", component="tool:search"),
        ]
        result = TestResult(
            test_id="t1", score=0.0, actual_output="wrong", trace=trace
        )
        attr = attributor.attribute(trace, result)
        # tool:search appeared twice, system_prompt once
        assert attr.component_scores["tool:search"] >= attr.component_scores["system_prompt"]
