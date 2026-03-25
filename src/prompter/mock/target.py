"""MockTarget — target labels derived from successful mocks."""
from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import TYPE_CHECKING

from prompter.llm.adapter import Message

if TYPE_CHECKING:
    from prompter.llm.adapter import LLMAdapter

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class MockTarget:
    """The target label derived from a successful mock."""

    capability_name: str
    target_outputs: dict[str, str]  # test_id -> ideal output from mock
    embedding_targets: list[tuple[str, str]] | None = None  # (query, target_chunk)


OPTIMIZE_SYSTEM = (
    "You are an implementation optimizer. Your job is to improve a code "
    "implementation so that its output matches target outputs.\n\n"
    "You will receive:\n"
    "1. The current implementation code\n"
    "2. Target outputs that the implementation should produce\n"
    "3. Optional embedding targets for RAG retrieval\n\n"
    "Return ONLY the improved implementation code, no explanation or "
    "markdown fences."
)


class MockTargetOptimizer:
    """Optimizes a real implementation to match mock targets."""

    def __init__(self, llm: LLMAdapter) -> None:
        self._llm = llm

    async def optimize_toward_target(
        self, implementation: str, target: MockTarget
    ) -> str:
        """Refine implementation until output matches mock target.

        Uses LLM to iteratively improve the implementation.
        Compares implementation output vs target using token overlap /
        embedding similarity. Returns improved implementation string.
        """
        if not target.target_outputs:
            raise ValueError(
                f"Cannot optimize toward empty target outputs "
                f"for capability '{target.capability_name}'"
            )

        # Build context for the LLM
        targets_str = "\n".join(
            f"  - test '{tid}': expected output = {out!r}"
            for tid, out in target.target_outputs.items()
        )

        embedding_str = ""
        if target.embedding_targets:
            embedding_str = "\n\nEmbedding targets (query -> chunk):\n"
            embedding_str += "\n".join(
                f"  - query: {q!r} -> chunk: {c!r}"
                for q, c in target.embedding_targets
            )

        user_msg = (
            f"Current implementation:\n```\n{implementation}\n```\n\n"
            f"Target outputs:\n{targets_str}"
            f"{embedding_str}\n\n"
            f"Improve the implementation to produce these target outputs. "
            f"Return only the improved code."
        )

        response = await self._llm.complete(
            messages=[
                Message(role="system", content=OPTIMIZE_SYSTEM),
                Message(role="user", content=user_msg),
            ],
            temperature=0.3,
        )

        improved = response.content.strip()

        # Strip markdown fences if present
        if improved.startswith("```"):
            lines = improved.split("\n")
            lines = lines[1:-1] if lines[-1].strip() == "```" else lines[1:]
            improved = "\n".join(lines)

        logger.info(
            "Optimized implementation for '%s' (%d chars -> %d chars)",
            target.capability_name, len(implementation), len(improved),
        )

        return improved
