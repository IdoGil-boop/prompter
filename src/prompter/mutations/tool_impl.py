"""ToolImplementationMutation — rewrites tool implementation code with validation."""
from __future__ import annotations

import ast
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

TOOL_IMPL_SYSTEM = (
    "You are a tool implementation expert. Your job is to rewrite "
    "a tool's Python implementation to fix bugs or improve behavior.\n\n"
    "You will receive:\n"
    "1. The tool name, description, and parameter schema\n"
    "2. The current implementation code\n"
    "3. Test cases that failed\n"
    "4. Rationale for the change\n\n"
    "Rules:\n"
    "- The implementation receives arguments as JSON via stdin\n"
    "- It should print the result to stdout\n"
    "- Use `import json, sys; args = json.loads(sys.stdin.read())` to read args\n"
    "- Output ONLY the Python code, no markdown fences\n"
    "- Must be valid Python that can run as a standalone script"
)


@register_mutation
class ToolImplementationMutation(Mutation):
    """Rewrites a tool's implementation code, validating syntax before accepting."""

    type_id = "tool_impl.modify"
    cost_tier = 4

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
            f"Description: {tool_spec.description}\n"
            f"Parameter schema: {tool_spec.parameters_schema}\n\n"
            f"Current implementation:\n```python\n{tool_spec.implementation}\n```\n\n"
            f"Number of failing tests: {len(failed)}\n"
            f"Rationale: {proposal.rationale}\n\n"
            f"Write the improved implementation:"
        )

        response = await self.llm.complete(
            messages=[
                Message(role="system", content=TOOL_IMPL_SYSTEM),
                Message(role="user", content=user_msg),
            ],
            temperature=0.7,
        )

        new_impl = _strip_fences(response.content.strip())

        # Validate syntax before accepting
        _validate_syntax(new_impl, tool_name)

        new_tool = ToolSpec(
            name=tool_spec.name,
            description=tool_spec.description,
            parameters_schema=tool_spec.parameters_schema,
            implementation=new_impl,
            enabled=tool_spec.enabled,
        )
        new_config = context.config.with_tool(tool_name, new_tool)

        return MutationResult(
            config=new_config,
            description=f"Rewrote implementation for tool '{tool_name}'",
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

    if context.config.tools:
        return next(iter(context.config.tools))

    raise ValueError("No tool name found in proposal and config has no tools")


def _validate_syntax(code: str, tool_name: str) -> None:
    """Check that code is valid Python. Raises ValueError on syntax errors."""
    try:
        ast.parse(code)
    except SyntaxError as exc:
        raise ValueError(
            f"New implementation for tool '{tool_name}' has syntax errors: {exc}"
        ) from exc


def _strip_fences(text: str) -> str:
    """Remove markdown code fences if present."""
    if text.startswith("```"):
        lines = text.split("\n")
        lines = lines[1:-1] if lines[-1].strip() == "```" else lines[1:]
        text = "\n".join(lines)
    return text
