"""Tests for ToolSandbox — subprocess-based tool execution with timeout."""
from __future__ import annotations

import pytest

from prompter.config.agent_config import ToolSpec
from prompter.runner.tool_sandbox import ToolSandbox


class TestToolSandbox:
    """ToolSandbox executes tool code in a subprocess with timeout."""

    async def test_execute_simple_tool_returns_stdout(self) -> None:
        """Execute a simple tool that reads JSON from stdin and prints result."""
        sandbox = ToolSandbox(timeout_seconds=5.0)
        tool = ToolSpec(
            name="add",
            description="Add two numbers",
            parameters_schema={
                "type": "object",
                "properties": {
                    "a": {"type": "number"},
                    "b": {"type": "number"},
                },
            },
            implementation=(
                "import json, sys\n"
                "args = json.loads(sys.stdin.read())\n"
                "print(args['a'] + args['b'])"
            ),
        )

        result = await sandbox.execute(tool, {"a": 3, "b": 4})
        assert result.strip() == "7"

    async def test_execute_timeout_raises(self) -> None:
        """Tool that exceeds timeout should raise TimeoutError."""
        sandbox = ToolSandbox(timeout_seconds=0.5)
        tool = ToolSpec(
            name="slow",
            description="A slow tool",
            parameters_schema={},
            implementation="import time; time.sleep(10)",
        )

        with pytest.raises(TimeoutError):
            await sandbox.execute(tool, {})

    async def test_execute_error_raises_runtime_error(self) -> None:
        """Tool that raises an exception should raise RuntimeError."""
        sandbox = ToolSandbox(timeout_seconds=5.0)
        tool = ToolSpec(
            name="bad",
            description="A tool that errors",
            parameters_schema={},
            implementation="raise ValueError('something went wrong')",
        )

        with pytest.raises(RuntimeError, match="something went wrong"):
            await sandbox.execute(tool, {})

    async def test_execute_forbidden_module(self) -> None:
        """Tool that imports a forbidden module should raise RuntimeError."""
        sandbox = ToolSandbox(timeout_seconds=5.0, allowed_modules=["json", "sys", "math"])
        tool = ToolSpec(
            name="hacker",
            description="Tries to import os",
            parameters_schema={},
            implementation=(
                "import os\n"
                "print(os.listdir('.'))"
            ),
        )

        with pytest.raises(RuntimeError):
            await sandbox.execute(tool, {})

    async def test_execute_with_allowed_modules(self) -> None:
        """Tool should work when using only allowed modules."""
        sandbox = ToolSandbox(timeout_seconds=5.0, allowed_modules=["json", "sys", "math"])
        tool = ToolSpec(
            name="sqrt",
            description="Square root",
            parameters_schema={"type": "object", "properties": {"n": {"type": "number"}}},
            implementation=(
                "import json, sys, math\n"
                "args = json.loads(sys.stdin.read())\n"
                "print(math.sqrt(args['n']))"
            ),
        )

        result = await sandbox.execute(tool, {"n": 16})
        assert result.strip() == "4.0"

    async def test_execute_empty_implementation(self) -> None:
        """Tool with empty implementation should raise RuntimeError."""
        sandbox = ToolSandbox(timeout_seconds=5.0)
        tool = ToolSpec(
            name="empty",
            description="Empty tool",
            parameters_schema={},
            implementation="",
        )

        with pytest.raises(RuntimeError, match="empty implementation"):
            await sandbox.execute(tool, {})
