"""Tests for MockTarget and MockTargetOptimizer."""
from __future__ import annotations

import pytest

from prompter.mock.target import MockTarget, MockTargetOptimizer
from tests.conftest import MockLLM


# ---------------------------------------------------------------------------
# MockTarget dataclass
# ---------------------------------------------------------------------------

class TestMockTarget:
    def test_create_target(self) -> None:
        target = MockTarget(
            capability_name="calculator",
            target_outputs={"t1": "42", "t2": "6"},
        )
        assert target.capability_name == "calculator"
        assert target.target_outputs["t1"] == "42"
        assert target.embedding_targets is None

    def test_create_target_with_embeddings(self) -> None:
        target = MockTarget(
            capability_name="rag_source",
            target_outputs={"t1": "answer"},
            embedding_targets=[("query1", "chunk1"), ("query2", "chunk2")],
        )
        assert len(target.embedding_targets) == 2
        assert target.embedding_targets[0] == ("query1", "chunk1")

    def test_target_is_frozen(self) -> None:
        target = MockTarget(
            capability_name="x",
            target_outputs={"t1": "y"},
        )
        with pytest.raises(AttributeError):
            target.capability_name = "z"  # type: ignore[misc]

    def test_empty_target_outputs_allowed(self) -> None:
        target = MockTarget(
            capability_name="x",
            target_outputs={},
        )
        assert target.target_outputs == {}


# ---------------------------------------------------------------------------
# MockTargetOptimizer
# ---------------------------------------------------------------------------

class TestMockTargetOptimizer:
    async def test_optimize_toward_target_returns_string(self) -> None:
        """optimize_toward_target should return an improved implementation string."""
        llm = MockLLM(responses=["def improved_impl(): return '42'"])
        optimizer = MockTargetOptimizer(llm=llm)

        target = MockTarget(
            capability_name="calculator",
            target_outputs={"t1": "42", "t2": "6"},
        )

        result = await optimizer.optimize_toward_target(
            implementation="def bad_impl(): return 'wrong'",
            target=target,
        )
        assert isinstance(result, str)
        assert len(result) > 0

    async def test_optimize_uses_llm(self) -> None:
        """LLM should receive context about implementation and targets."""
        call_log: list[str] = []

        def track_calls(msgs: list) -> str:
            user_msg = [m for m in msgs if m.role == "user"]
            if user_msg:
                call_log.append(user_msg[-1].content)
            return "def optimized(): return '42'"

        llm = MockLLM(responses=track_calls)
        optimizer = MockTargetOptimizer(llm=llm)

        target = MockTarget(
            capability_name="calculator",
            target_outputs={"t1": "42"},
        )

        await optimizer.optimize_toward_target(
            implementation="def bad(): pass",
            target=target,
        )

        # LLM should have been called with context about the implementation
        assert len(call_log) >= 1
        # The prompt should mention the target outputs
        assert "42" in call_log[0]

    async def test_optimize_with_embedding_targets(self) -> None:
        """Should handle targets that include embedding targets for RAG."""
        llm = MockLLM(responses=["def rag_impl(): return 'chunk'"])
        optimizer = MockTargetOptimizer(llm=llm)

        target = MockTarget(
            capability_name="rag_source",
            target_outputs={"t1": "answer"},
            embedding_targets=[("query", "target_chunk")],
        )

        result = await optimizer.optimize_toward_target(
            implementation="def rag(): pass",
            target=target,
        )
        assert isinstance(result, str)

    async def test_optimize_empty_target_raises(self) -> None:
        """Empty target_outputs should raise ValueError."""
        llm = MockLLM(responses=["irrelevant"])
        optimizer = MockTargetOptimizer(llm=llm)

        target = MockTarget(
            capability_name="empty",
            target_outputs={},
        )

        with pytest.raises(ValueError, match="empty"):
            await optimizer.optimize_toward_target(
                implementation="def x(): pass",
                target=target,
            )
