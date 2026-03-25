"""AddToolMutation and RemoveToolMutation — add or remove tools from config."""
from __future__ import annotations

import json
import logging
from typing import Any

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

ADD_TOOL_SYSTEM = (
    "You are a tool design expert. Your job is to create a new tool "
    "for an LLM agent based on test failures.\n\n"
    "You will receive:\n"
    "1. The current system prompt and existing tools\n"
    "2. Test cases that failed\n"
    "3. Rationale for adding a tool\n\n"
    "Output a JSON object with these fields:\n"
    '- "name": tool name (snake_case)\n'
    '- "description": what the tool does\n'
    '- "parameters_schema": JSON Schema for parameters\n'
    '- "implementation": Python code that reads JSON from stdin and prints result\n\n'
    "Output ONLY the JSON, no markdown fences."
)

REMOVE_TOOL_SYSTEM = (
    "You are a tool optimization expert. Your job is to identify "
    "which tool should be removed from an agent's toolset.\n\n"
    "You will receive:\n"
    "1. The current tools\n"
    "2. Test performance summary\n"
    "3. Rationale for removal\n\n"
    "Output ONLY the name of the tool to remove, nothing else."
)


@register_mutation
class AddToolMutation(Mutation):
    """Adds a new tool to the agent config."""

    type_id = "tool.add"
    cost_tier = 5

    def __init__(self, llm: LLMAdapter) -> None:
        self.llm = llm

    async def apply(
        self, context: MutationContext, proposal: MutationProposal
    ) -> MutationResult:
        existing_tools = ", ".join(context.config.tools.keys()) or "none"
        failed = [r for r in context.eval_report.results if r.score < 1.0]

        user_msg = (
            f"System prompt: {context.config.system_prompt[:200]}\n"
            f"Existing tools: {existing_tools}\n"
            f"Number of failing tests: {len(failed)}\n"
            f"Rationale: {proposal.rationale}\n\n"
            f"Design the new tool as JSON:"
        )

        response = await self.llm.complete(
            messages=[
                Message(role="system", content=ADD_TOOL_SYSTEM),
                Message(role="user", content=user_msg),
            ],
            temperature=0.7,
        )

        tool_data = _parse_json(response.content, context_label="AddToolMutation")
        if not tool_data.get("implementation"):
            raise ValueError("LLM returned tool with empty implementation")
        tool_spec = ToolSpec(
            name=tool_data["name"],
            description=tool_data.get("description", ""),
            parameters_schema=tool_data.get("parameters_schema", {}),
            implementation=tool_data.get("implementation", ""),
            enabled=True,
        )

        new_config = context.config.with_tool(tool_spec.name, tool_spec)

        return MutationResult(
            config=new_config,
            description=f"Added new tool '{tool_spec.name}'",
            mutation_type=self.type_id,
            components_touched=[f"tool:{tool_spec.name}"],
        )


@register_mutation
class RemoveToolMutation(Mutation):
    """Removes a tool from the agent config."""

    type_id = "tool.remove"
    cost_tier = 5

    def __init__(self, llm: LLMAdapter) -> None:
        self.llm = llm

    async def apply(
        self, context: MutationContext, proposal: MutationProposal
    ) -> MutationResult:
        tool_name = _get_tool_name(context, proposal)

        if tool_name not in context.config.tools:
            raise ValueError(
                f"Tool '{tool_name}' not found in config. "
                f"Available: {list(context.config.tools.keys())}"
            )

        new_config = context.config.without_tool(tool_name)

        return MutationResult(
            config=new_config,
            description=f"Removed tool '{tool_name}'",
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

    raise ValueError("No tool name specified for removal")


def _parse_json(text: str, context_label: str = "tool_manage") -> dict[str, Any]:
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
