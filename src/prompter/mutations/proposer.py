from __future__ import annotations

import json
import logging
from typing import TYPE_CHECKING

from prompter.llm.adapter import LLMAdapter, Message
from prompter.mutations.base import MutationContext, MutationProposal

if TYPE_CHECKING:
    from prompter.mutations.ladder import LadderState

logger = logging.getLogger(__name__)

PROPOSER_SYSTEM = (
    "You are an agent optimization strategist. Given test failures and the "
    "current agent configuration, propose exactly ONE targeted mutation to "
    "improve performance.\n\n"
    "You must output valid JSON with these fields:\n"
    "{\n"
    '  "mutation_type": "<type from allowed list>",\n'
    '  "rationale": "<why this specific change will help>",\n'
    '  "target_tests": ["<test_ids this targets>"],\n'
    '  "target_components": ["<component names affected>"],\n'
    '  "params": {}\n'
    "}\n\n"
    "Principles:\n"
    "- Target the highest-impact failure first\n"
    "- Prefer the cheapest mutation type that could fix the issue\n"
    "- Don't repeat mutations that were already tried and reverted\n"
    "- Be specific about what to change and why"
)


class MutationProposer:
    """Analyzes failures and proposes targeted mutations."""

    def __init__(self, llm: LLMAdapter):
        self.llm = llm

    async def propose(
        self,
        context: MutationContext,
        ladder: LadderState,
    ) -> MutationProposal:
        allowed_types = ladder.get_allowed_types()
        failed = [r for r in context.eval_report.results if r.score < 1.0]

        failures_text = "\n".join(
            f"- Test '{r.test_id}': score={r.score:.2f}, "
            f"got='{r.actual_output[:200]}'"
            + (f", error='{r.error}'" if r.error else "")
            for r in failed
        )

        history_text = "\n".join(
            f"- [{('kept' if h.get('accepted') else 'reverted')}] "
            f"type={h.get('mutation_type')}: {h.get('description', '')}"
            for h in context.history[-10:]
        ) or "No previous mutations."

        attribution_text = ""
        if context.attribution_hints:
            sorted_hints = sorted(
                context.attribution_hints.items(),
                key=lambda x: x[1],
                reverse=True,
            )
            attribution_text = (
                "Component attribution (highest impact first):\n"
                + "\n".join(
                    f"  {comp}: {score:.2f}"
                    for comp, score in sorted_hints[:5]
                )
            )

        config_summary = (
            f"System prompt ({len(context.config.system_prompt)} chars): "
            f"{context.config.system_prompt[:200]}...\n"
            f"Tools: {list(context.config.tools.keys()) or 'none'}\n"
            f"RAG: {'configured' if context.config.rag_config else 'none'}\n"
            f"Context strategy: "
            f"{'configured' if context.config.context_strategy else 'none'}\n"
            f"Memory: "
            f"{'configured' if context.config.memory_strategy else 'none'}"
        )

        user_msg = (
            f"Allowed mutation types: {allowed_types}\n\n"
            f"Current config:\n{config_summary}\n\n"
            f"Failed tests:\n{failures_text}\n\n"
            f"Mutation history:\n{history_text}\n\n"
            f"{attribution_text}\n\n"
            f"Propose ONE mutation:"
        )

        response = await self.llm.complete(
            messages=[
                Message(role="system", content=PROPOSER_SYSTEM),
                Message(role="user", content=user_msg),
            ],
            temperature=0.4,
        )

        return _parse_proposal(response.content, allowed_types)


def _parse_proposal(
    content: str, allowed_types: list[str]
) -> MutationProposal:
    if not allowed_types:
        raise ValueError(
            "allowed_types must not be empty — "
            "no mutation types are available"
        )
    content = content.strip()
    if content.startswith("```"):
        lines = content.split("\n")
        content = (
            "\n".join(lines[1:-1])
            if lines[-1].strip().startswith("```")
            else content
        )

    try:
        data = json.loads(content)
    except json.JSONDecodeError:
        start = content.find("{")
        end = content.rfind("}") + 1
        if start >= 0 and end > start:
            data = json.loads(content[start:end])
        else:
            raise ValueError(
                "Could not parse proposal JSON from LLM output: "
                f"{content[:200]}"
            ) from None

    mutation_type: str = data["mutation_type"]
    if mutation_type not in allowed_types:
        logger.warning(
            "LLM proposed type '%s' not in allowed %s, defaulting to '%s'",
            mutation_type, allowed_types, allowed_types[0],
        )
        mutation_type = allowed_types[0]

    return MutationProposal(
        mutation_type=mutation_type,
        rationale=data.get("rationale", ""),
        target_tests=data.get("target_tests", []),
        target_components=data.get("target_components", []),
        cost_tier=_tier_for_type(mutation_type),
        params=data.get("params", {}),
    )


def _tier_for_type(mutation_type: str) -> int:
    from prompter.mutations.ladder import ESCALATION_TIERS

    for tier_info in ESCALATION_TIERS:
        if mutation_type in tier_info["types"]:
            return tier_info["tier"]
    return 1
