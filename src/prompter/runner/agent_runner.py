"""AgentRunner — wraps AgentConfig + LLMAdapter into AgentFn callable."""
from __future__ import annotations

import logging
import time
from typing import TYPE_CHECKING, Any

from prompter.eval.evaluator import TraceEvent
from prompter.llm.adapter import LLMAdapter, Message, ToolDefinition

if TYPE_CHECKING:
    from prompter.config.agent_config import AgentConfig
    from prompter.runner.tool_sandbox import ToolSandbox

logger = logging.getLogger(__name__)

DEFAULT_MAX_TOOL_ROUNDS = 10


class AgentRunner:
    """Wraps an AgentConfig + LLMAdapter into the AgentFn protocol."""

    def __init__(
        self,
        config: AgentConfig,
        llm: LLMAdapter,
        sandbox: ToolSandbox | None = None,
        max_tool_rounds: int = DEFAULT_MAX_TOOL_ROUNDS,
    ) -> None:
        self._config = config
        self._llm = llm
        self._sandbox = sandbox
        self._max_tool_rounds = max_tool_rounds
        self.trace_events: list[TraceEvent] = []

    async def run(
        self, input_text: str, context: dict[str, Any] | None = None
    ) -> str:
        """Send input through the agent config and return output.

        Handles multi-turn tool call loop: LLM may return tool_calls,
        which are executed via sandbox, results appended, and LLM called again.
        """
        messages: list[Message] = [
            Message(role="system", content=self._config.system_prompt),
            Message(role="user", content=input_text),
        ]

        tools = self._build_tool_definitions()

        for _round in range(self._max_tool_rounds):
            start = time.monotonic()
            response = await self._llm.complete(messages=messages, tools=tools)
            latency_ms = (time.monotonic() - start) * 1000

            self.trace_events.append(
                TraceEvent(
                    timestamp=time.time(),
                    event_type="llm_call",
                    component="system_prompt",
                    data={
                        "input": input_text,
                        "output": response.content,
                        "latency_ms": latency_ms,
                        "usage": {
                            "prompt_tokens": response.usage.prompt_tokens,
                            "completion_tokens": response.usage.completion_tokens,
                        },
                    },
                )
            )

            # No tool calls — return text response
            if not response.tool_calls:
                return response.content

            # Tool calls received but no sandbox
            if self._sandbox is None:
                logger.warning(
                    "LLM returned %d tool call(s) but no sandbox configured; "
                    "returning text content",
                    len(response.tool_calls),
                )
                return response.content

            # Append assistant message with tool calls
            messages.append(
                Message(
                    role="assistant",
                    content=response.content,
                    tool_calls=response.tool_calls,
                )
            )

            # Execute each tool call
            for tc in response.tool_calls:
                tool_spec = self._config.tools.get(tc.name)
                if tool_spec is None:
                    tool_result = f"Error: unknown tool '{tc.name}'"
                    logger.warning("LLM called unknown tool: %s", tc.name)
                else:
                    try:
                        tool_result = await self._sandbox.execute(
                            tool_spec, tc.arguments
                        )
                    except Exception as exc:
                        tool_result = f"Error: {exc}"
                        logger.warning(
                            "Tool '%s' execution failed: %s", tc.name, exc
                        )

                self.trace_events.append(
                    TraceEvent(
                        timestamp=time.time(),
                        event_type="tool_call",
                        component=f"tool:{tc.name}",
                        data={
                            "tool_call_id": tc.id,
                            "arguments": tc.arguments,
                            "result": tool_result,
                        },
                    )
                )

                messages.append(
                    Message(
                        role="tool",
                        content=tool_result,
                        tool_call_id=tc.id,
                    )
                )

        # Exhausted max rounds — call LLM one final time without tools
        # so it synthesizes a proper response from all tool results
        logger.warning(
            "Reached max tool rounds (%d); calling LLM without tools to synthesize final answer",
            self._max_tool_rounds,
        )
        response = await self._llm.complete(messages=messages, tools=None)
        return response.content

    def as_agent_fn(self) -> AgentFnCallable:
        """Return a callable matching the AgentFn protocol."""
        return AgentFnCallable(self)

    def _build_tool_definitions(self) -> list[ToolDefinition] | None:
        """Convert enabled ToolSpecs to ToolDefinitions, or None if no tools."""
        enabled_tools = [
            spec for spec in self._config.tools.values() if spec.enabled
        ]
        if not enabled_tools:
            return None

        return [
            ToolDefinition(
                name=spec.name,
                description=spec.description,
                parameters=spec.parameters_schema,
            )
            for spec in enabled_tools
        ]


class AgentFnCallable:
    """Wraps AgentRunner.run to match the AgentFn protocol signature."""

    def __init__(self, runner: AgentRunner) -> None:
        self._runner = runner

    async def __call__(
        self, input_text: str, context: dict[str, Any] | None = None
    ) -> str:
        return await self._runner.run(input_text, context)
