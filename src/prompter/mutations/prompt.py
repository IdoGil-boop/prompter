from __future__ import annotations

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

PROMPT_MUTATION_SYSTEM = (
    "You are a prompt optimization expert. Your job is to improve "
    "a system prompt based on test failures.\n\n"
    "You will receive:\n"
    "1. The current system prompt\n"
    "2. Test cases that failed (input, expected output, actual output)\n"
    "3. History of previous mutation attempts\n\n"
    "Rules:\n"
    "- Make ONE targeted change to address the failures\n"
    "- Preserve everything that's already working\n"
    "- Be specific in your instructions, not vague\n"
    "- Output ONLY the new system prompt, nothing else"
)


@register_mutation
class SystemPromptMutation(Mutation):
    type_id = "prompt.rewrite"
    cost_tier = 1

    def __init__(self, llm: LLMAdapter):
        self.llm = llm

    async def apply(self, context: MutationContext, proposal: MutationProposal) -> MutationResult:
        failed = [r for r in context.eval_report.results if r.score < 1.0]
        test_map = {t.id: t for t in _get_tests_from_context(context)}

        failure_descriptions = []
        for result in failed:
            test = test_map.get(result.test_id)
            if test:
                failure_descriptions.append(
                    f"Input: {test.input}\n"
                    f"Expected: {test.expected}\n"
                    f"Got: {result.actual_output}\n"
                    f"Score: {result.score:.2f}"
                )

        history_summary = _format_history(context.history, "prompt.rewrite")

        user_msg = (
            f"Current system prompt:\n```\n{context.config.system_prompt}\n```\n\n"
            f"Failed tests:\n{'---'.join(failure_descriptions)}\n\n"
            f"Previous attempts:\n{history_summary}\n\n"
            f"Rationale for this change: {proposal.rationale}\n\n"
            f"Write the improved system prompt:"
        )

        response = await self.llm.complete(
            messages=[
                Message(role="system", content=PROMPT_MUTATION_SYSTEM),
                Message(role="user", content=user_msg),
            ],
            temperature=0.7,
        )

        new_prompt = response.content.strip()
        if new_prompt.startswith("```"):
            lines = new_prompt.split("\n")
            new_prompt = "\n".join(lines[1:-1]) if lines[-1].strip() == "```" else new_prompt

        new_config = context.config.with_system_prompt(new_prompt)

        return MutationResult(
            config=new_config,
            description=f"Rewrote system prompt targeting {len(failed)} failing tests",
            mutation_type=self.type_id,
            components_touched=["system_prompt"],
        )


def _get_tests_from_context(context: MutationContext) -> list[Any]:
    """Extract test cases from the context's test_suite if available."""
    if context.test_suite is not None:
        return list(context.test_suite.tests)
    return []


def _format_history(history: list[dict[str, Any]], mutation_type: str) -> str:
    relevant = [h for h in history if h.get("mutation_type") == mutation_type]
    if not relevant:
        return "No previous attempts."
    lines = []
    for h in relevant[-5:]:
        status = "kept" if h.get("accepted") else "reverted"
        lines.append(f"- [{status}] {h.get('description', 'unknown')}")
    return "\n".join(lines)
