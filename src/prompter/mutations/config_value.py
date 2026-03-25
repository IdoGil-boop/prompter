"""ConfigValueMutation — adjusts values in rag_config, context_strategy, or memory_strategy."""
from __future__ import annotations

import json
import logging
from typing import Any

from prompter.llm.adapter import LLMAdapter, Message
from prompter.mutations.base import (
    Mutation,
    MutationContext,
    MutationProposal,
    MutationResult,
    register_mutation,
)

logger = logging.getLogger(__name__)

CONFIG_VALUE_SYSTEM = (
    "You are a configuration tuning expert. Your job is to adjust "
    "config values for an LLM agent based on test performance.\n\n"
    "You will receive:\n"
    "1. The config section name (rag_config, context_strategy, or memory_strategy)\n"
    "2. The current config values as JSON\n"
    "3. Test performance summary\n"
    "4. Rationale for the change\n\n"
    "Rules:\n"
    "- Make targeted adjustments to improve performance\n"
    "- Preserve keys that are working well\n"
    "- Output ONLY valid JSON with the new config values, nothing else"
)

_TARGET_TO_BUILDER = {
    "rag_config": "with_rag_config",
    "context_strategy": "with_context_strategy",
    "memory_strategy": "with_memory_strategy",
}


@register_mutation
class ConfigValueMutation(Mutation):
    """Adjusts values in rag_config, context_strategy, or memory_strategy."""

    type_id = "config.adjust"
    cost_tier = 3

    def __init__(self, llm: LLMAdapter) -> None:
        self.llm = llm

    async def apply(
        self, context: MutationContext, proposal: MutationProposal
    ) -> MutationResult:
        target = _get_target(context, proposal)
        current_value = getattr(context.config, target, None) or {}

        failed = [r for r in context.eval_report.results if r.score < 1.0]

        user_msg = (
            f"Config section: {target}\n"
            f"Current values:\n```json\n{json.dumps(current_value, indent=2)}\n```\n\n"
            f"Aggregate score: {context.eval_report.aggregate_score:.2f}\n"
            f"Failing tests: {len(failed)}\n"
            f"Rationale: {proposal.rationale}\n\n"
            f"Output the adjusted config as JSON:"
        )

        response = await self.llm.complete(
            messages=[
                Message(role="system", content=CONFIG_VALUE_SYSTEM),
                Message(role="user", content=user_msg),
            ],
            temperature=0.3,
        )

        new_value = _parse_json(response.content, context_label="ConfigValueMutation")
        builder_method = _TARGET_TO_BUILDER[target]
        new_config = getattr(context.config, builder_method)(new_value)

        return MutationResult(
            config=new_config,
            description=f"Adjusted {target} config values",
            mutation_type=self.type_id,
            components_touched=[target],
        )


def _get_target(context: MutationContext, proposal: MutationProposal) -> str:
    """Extract target config section from proposal."""
    if "target" in proposal.params:
        target = str(proposal.params["target"])
        if target in _TARGET_TO_BUILDER:
            return target

    for comp in proposal.target_components:
        if comp in _TARGET_TO_BUILDER:
            return comp

    raise ValueError(
        f"Invalid config target. Must be one of: {list(_TARGET_TO_BUILDER.keys())}"
    )


def _parse_json(text: str, context_label: str = "config_value") -> dict[str, Any]:
    """Parse JSON from LLM response, stripping markdown fences if present."""
    text = text.strip()
    if text.startswith("```"):
        lines = text.split("\n")
        lines = lines[1:-1] if lines[-1].strip() == "```" else lines[1:]
        text = "\n".join(lines)
    try:
        result: dict[str, Any] = json.loads(text)
    except json.JSONDecodeError as exc:
        raise ValueError(
            f"Failed to parse LLM response as JSON for {context_label}: {text[:200]}"
        ) from exc
    return result
