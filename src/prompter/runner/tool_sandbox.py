"""ToolSandbox — executes tool code in a subprocess with timeout."""
from __future__ import annotations

import asyncio
import json
import logging
import sys
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from prompter.config.agent_config import ToolSpec

logger = logging.getLogger(__name__)


class ToolSandbox:
    """Executes tool implementation code in an isolated subprocess with timeout.

    Security notes:
    - Code runs in a subprocess (not in-process exec)
    - Hard timeout via asyncio process wait
    - Optional module allowlist restricts imports
    - For production use, recommend running inside a container
    - No network/filesystem sandboxing in this MVP
    """

    def __init__(
        self,
        timeout_seconds: float = 30.0,
        allowed_modules: list[str] | None = None,
    ) -> None:
        self._timeout = timeout_seconds
        self._allowed_modules = allowed_modules

    async def execute(self, tool_spec: ToolSpec, arguments: dict[str, Any]) -> str:
        """Run tool implementation with given arguments, return string result.

        Args:
            tool_spec: The tool specification containing implementation code.
            arguments: JSON-serializable arguments to pass via stdin.

        Returns:
            stdout output from the tool execution.

        Raises:
            RuntimeError: If the tool fails (non-zero exit, empty implementation).
            TimeoutError: If the tool exceeds the configured timeout.
        """
        if not tool_spec.implementation.strip():
            raise RuntimeError(f"Tool '{tool_spec.name}' has empty implementation")

        code = self._build_code(tool_spec.implementation)
        args_json = json.dumps(arguments)

        try:
            process = await asyncio.create_subprocess_exec(
                sys.executable, "-c", code,
                stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )

            stdout_bytes, stderr_bytes = await asyncio.wait_for(
                process.communicate(input=args_json.encode()),
                timeout=self._timeout,
            )
        except TimeoutError:
            # Kill the process on timeout
            try:
                process.kill()
                await process.wait()
            except ProcessLookupError:
                pass
            raise TimeoutError(
                f"Tool '{tool_spec.name}' exceeded timeout of {self._timeout}s"
            ) from None

        stdout = stdout_bytes.decode() if stdout_bytes else ""
        stderr = stderr_bytes.decode() if stderr_bytes else ""

        if stderr:
            logger.debug("Tool '%s' stderr: %s", tool_spec.name, stderr.strip())

        if process.returncode != 0:
            raise RuntimeError(
                f"Tool '{tool_spec.name}' failed (exit {process.returncode}): "
                f"{stderr.strip()}"
            )

        return stdout

    def _build_code(self, implementation: str) -> str:
        """Build the Python code to execute, optionally with import restrictions."""
        if self._allowed_modules is None:
            return implementation

        # Build an import hook that restricts which modules can be imported
        allowed_set = repr(set(self._allowed_modules))
        # Pre-import allowed modules so their transitive deps are cached in
        # sys.modules, then install the import hook. The hook allows:
        # 1. Modules already loaded as transitive deps of allowed modules
        # 2. Modules whose top-level name is in the allowed list
        # 3. Internal modules (starting with _)
        preload_lines = "\n".join(
            f"import {mod}" for mod in self._allowed_modules
        )
        guard = (
            "import builtins as _builtins, sys as _sys\n"
            f"{preload_lines}\n"
            f"_allowed = {allowed_set}\n"
            "_preloaded = set(_sys.modules.keys())\n"
            "_original_import = _builtins.__import__\n"
            "_in_allowed_import = False\n"
            "def _restricted_import(name, *args, **kwargs):\n"
            "    global _in_allowed_import\n"
            "    if _in_allowed_import:\n"
            "        return _original_import(name, *args, **kwargs)\n"
            "    top = name.split('.')[0]\n"
            "    if top not in _allowed and top != 'builtins' and not top.startswith('_'):\n"
            "        raise ImportError(f'Module {name!r} is not in the allowed list')\n"
            "    _in_allowed_import = True\n"
            "    try:\n"
            "        return _original_import(name, *args, **kwargs)\n"
            "    finally:\n"
            "        _in_allowed_import = False\n"
            "_builtins.__import__ = _restricted_import\n"
        )
        return guard + implementation
