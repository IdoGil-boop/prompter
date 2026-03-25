from __future__ import annotations

import logging
import time
from typing import Any, Literal

import httpx

from prompter.llm.adapter import (
    LLMResponse,
    Message,
    TokenUsage,
    ToolDefinition,
)

logger = logging.getLogger(__name__)


class OllamaAdapter:
    """Adapter for local Ollama instance."""

    def __init__(
        self,
        base_url: str = "http://localhost:11434",
        model: str = "llama3.2",
        timeout: float = 300.0,
    ):
        self._base_url = base_url.rstrip("/")
        self._model = model
        self._client = httpx.AsyncClient(
            base_url=self._base_url,
            timeout=timeout,
        )

    @property
    def model_id(self) -> str:
        return f"ollama/{self._model}"

    @property
    def tier(self) -> Literal["local", "cheap", "sota"]:
        return "local"

    async def complete(
        self,
        messages: list[Message],
        tools: list[ToolDefinition] | None = None,
        temperature: float = 0.0,
        max_tokens: int = 4096,
    ) -> LLMResponse:
        payload: dict[str, Any] = {
            "model": self._model,
            "messages": [m.to_dict() for m in messages],
            "stream": False,
            "options": {
                "temperature": temperature,
                "num_predict": max_tokens,
            },
        }

        start = time.monotonic()
        response = await self._client.post("/api/chat", json=payload)
        latency = (time.monotonic() - start) * 1000

        response.raise_for_status()
        data = response.json()

        content = data.get("message", {}).get("content", "")
        usage = TokenUsage(
            prompt_tokens=data.get("prompt_eval_count", 0),
            completion_tokens=data.get("eval_count", 0),
        )

        return LLMResponse(
            content=content,
            tool_calls=[],
            usage=usage,
            latency_ms=latency,
        )

    async def __aenter__(self) -> OllamaAdapter:
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: Any,
    ) -> None:
        await self.close()

    async def close(self) -> None:
        await self._client.aclose()
