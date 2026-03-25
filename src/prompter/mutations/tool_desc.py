"""ToolDescriptionMutation — rewrites a tool's description to improve LLM usage."""
from __future__ import annotations

import logging

from prompter.config.agent_config import ToolSpec
from prompter.llm.adapter import LLMAdapter, Message
from prompter.mutations.base import (
    Mutation,
    MutationContext,
    MutationProposal,
    MutationResult,
    register_mutation,
)

logger = logging.getLogger(__name__)

TOOL_DESC_SYSTEM = (
    "You are a tool description optimization expert. Your job is to improve "
    "a tool's description so that an LLM agent uses it correctly.\n\n"
    "You will receive:\n"
    "1. The tool name and current description\n"
    "2. The tool's parameter schema\n"
    "3. Test cases that failed (the LLM may have called the wrong tool or passed wrong args)\n"
    "4. Rationale for the change\n\n"
    "Rules:\n"
    "- Make the description clear and specific\n"
    "- Describe when to use this tool and what it returns\n"
    "- Include parameter expectations if helpful\n"
    "- Output ONLY the new description text, nothing else"
)


@register_mutation
class ToolDescriptionMutation(Mutation):
    """Rewrites a tool's description to help the LLM use it correctly."""

    type_id = "tool_desc.edit"
    cost_tier = 2

    def __init__(self, llm: LLMAdapter) -> None:
        self.llm = llm

    async def apply(
        self, context: MutationContext, proposal: MutationProposal
    ) -> MutationResult:
        tool_name = _get_tool_name(context, proposal)
        tool_spec = context.config.tools[tool_name]

        failed = [r for r in context.eval_report.results if r.score < 1.0]

        user_msg = (
            f"Tool name: {tool_name}\n"
            f"Current description: {tool_spec.description}\n"
            f"Parameter schema: {tool_spec.parameters_schema}\n\n"
            f"Number of failing tests: {len(failed)}\n"
            f"Rationale: {proposal.rationale}\n\n"
            f"Write the improved tool description:"
        )

        response = await self.llm.complete(
            messages=[
                Message(role="system", content=TOOL_DESC_SYSTEM),
                Message(role="user", content=user_msg),
            ],
            temperature=0.7,
        )

        new_description = response.content.strip().strip('"').strip("'")

        new_tool = ToolSpec(
            name=tool_spec.name,
            description=new_description,
            parameters_schema=tool_spec.parameters_schema,
            implementation=tool_spec.implementation,
            enabled=tool_spec.enabled,
        )
        new_config = context.config.with_tool(tool_name, new_tool)

        return MutationResult(
            config=new_config,
            description=f"Rewrote description for tool '{tool_name}'",
            mutation_type=self.type_id,
            components_touched=[f"tool:{tool_name}"],
        )


def _get_tool_name(
    context: MutationContext, proposal: MutationProposal
) -> str:
    """Extract tool name from proposal params or target_components."""
    if "tool_name" in proposal.params:
        return str(proposal.params["tool_name"])

    for comp in proposal.target_components:
        if comp.startswith("tool:"):
            return comp[5:]

    # Fallback: first tool in config
    if context.config.tools:
        return next(iter(context.config.tools))

    raise ValueError("No tool name found in proposal and config has no tools")
