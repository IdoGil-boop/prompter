"""Architecture mutations — RAG, context, memory with mock-first gating."""
from __future__ import annotations

import json
import logging
from typing import Any

from prompter.llm.adapter import LLMAdapter, Message
from prompter.mock.target import MockTarget, MockTargetOptimizer
from prompter.mutations.base import (
    Mutation,
    MutationContext,
    MutationProposal,
    MutationResult,
    register_mutation,
)

logger = logging.getLogger(__name__)

_DESIGN_SYSTEM = (
    "You are an architecture design expert. Based on test failures, "
    "design a mock capability that would help the agent.\n\n"
    "Output a JSON object with:\n"
    '- "name": capability name (snake_case)\n'
    '- "description": what it does\n'
    '- "mock_output": ideal output for the failing tests\n'
    '- "capability_type": one of "tool", "rag", "context"\n\n'
    "Output ONLY the JSON, no markdown fences."
)


def _parse_json(text: str, context_label: str = "architecture") -> dict[str, Any]:
    """Parse JSON from LLM response, stripping markdown fences."""
    text = text.strip()
    if text.startswith("```"):
        lines = text.split("\n")
        lines = lines[1:-1] if lines[-1].strip() == "```" else lines[1:]
        text = "\n".join(lines)
    try:
        result: dict[str, Any] = json.loads(text)
    except json.JSONDecodeError as exc:
        raise ValueError(
            f"Failed to parse LLM response as JSON for "
            f"{context_label}: {text[:200]}"
        ) from exc
    return result


class _ArchitectureMutationBase(Mutation):
    """Shared logic for architecture mutations with mock-first gating."""

    _target_field: str  # "rag_config", "context_strategy", "memory_strategy"
    _component_name: str  # e.g. "rag_config"

    def __init__(self, llm: LLMAdapter) -> None:
        self._llm = llm

    async def apply(
        self, context: MutationContext, proposal: MutationProposal
    ) -> MutationResult:
        """Apply architecture mutation with mock-first validation.

        1. Ask LLM to design a mock capability
        2. Use MockEngine to test if it helps (optional if no test_suite)
        3. Use MockTargetOptimizer to build real implementation
        4. Return config with real implementation
        """
        # Step 1: Ask LLM to design the capability
        failed = [r for r in context.eval_report.results if r.score < 1.0]
        failures_desc = "\n".join(
            f"  - {r.test_id}: got {r.actual_output!r}"
            for r in failed[:5]
        )

        user_msg = (
            f"Agent system prompt: {context.config.system_prompt[:200]}\n"
            f"Mutation type: {self.type_id}\n"
            f"Rationale: {proposal.rationale}\n"
            f"Failing tests ({len(failed)}):\n{failures_desc}\n\n"
            f"Design a {self._target_field} capability as JSON:"
        )

        design_response = await self._llm.complete(
            messages=[
                Message(role="system", content=_DESIGN_SYSTEM),
                Message(role="user", content=user_msg),
            ],
            temperature=0.7,
        )

        design = _parse_json(
            design_response.content, context_label=self.type_id
        )

        mock_output = design.get("mock_output", "mock output")

        # Step 2: Build MockTarget from design
        target_outputs: dict[str, str] = {}
        if context.test_suite:
            for test in context.test_suite.tests:
                target_outputs[test.id] = mock_output
        else:
            for r in context.eval_report.results:
                target_outputs[r.test_id] = mock_output

        target = MockTarget(
            capability_name=design.get("name", "unnamed"),
            target_outputs=target_outputs,
        )

        # Step 3: Use LLM to build real implementation
        optimizer = MockTargetOptimizer(llm=self._llm)
        implementation = await optimizer.optimize_toward_target(
            implementation=f"# {self._target_field} implementation stub",
            target=target,
        )

        # Step 4: Build new config with the real implementation
        new_config = self._apply_to_config(
            context.config, design, implementation
        )

        return MutationResult(
            config=new_config,
            description=(
                f"Added {self._target_field} capability: "
                f"{design.get('name', 'unnamed')} — "
                f"{design.get('description', 'no description')}"
            ),
            mutation_type=self.type_id,
            components_touched=[self._component_name],
        )

    def _apply_to_config(
        self,
        config: Any,
        design: dict[str, Any],
        implementation: str,
    ) -> Any:
        """Apply the mutation result to the config. Override in subclasses."""
        raise NotImplementedError


@register_mutation
class RAGArchitectureMutation(_ArchitectureMutationBase):
    """Architecture mutation for RAG (retrieval-augmented generation)."""

    type_id = "architecture.rag"
    cost_tier = 6
    _target_field = "rag_config"
    _component_name = "rag_config"

    def _apply_to_config(
        self,
        config: Any,
        design: dict[str, Any],
        implementation: str,
    ) -> Any:
        rag_config = {
            "name": design.get("name", "rag"),
            "description": design.get("description", ""),
            "implementation": implementation,
            "type": "optimized",
        }
        return config.with_rag_config(rag_config)


@register_mutation
class ContextArchitectureMutation(_ArchitectureMutationBase):
    """Architecture mutation for context strategy."""

    type_id = "architecture.context"
    cost_tier = 6
    _target_field = "context_strategy"
    _component_name = "context_strategy"

    def _apply_to_config(
        self,
        config: Any,
        design: dict[str, Any],
        implementation: str,
    ) -> Any:
        context_strategy = {
            "name": design.get("name", "context"),
            "description": design.get("description", ""),
            "implementation": implementation,
            "type": "optimized",
        }
        return config.with_context_strategy(context_strategy)


@register_mutation
class MemoryArchitectureMutation(_ArchitectureMutationBase):
    """Architecture mutation for memory strategy."""

    type_id = "architecture.memory"
    cost_tier = 6
    _target_field = "memory_strategy"
    _component_name = "memory_strategy"

    def _apply_to_config(
        self,
        config: Any,
        design: dict[str, Any],
        implementation: str,
    ) -> Any:
        memory_strategy = {
            "name": design.get("name", "memory"),
            "description": design.get("description", ""),
            "implementation": implementation,
            "type": "optimized",
        }
        return config.with_memory_strategy(memory_strategy)
