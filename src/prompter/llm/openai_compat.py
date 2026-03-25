from __future__ import annotations

import json
import logging
import time
from typing import Any, Literal

import httpx

from prompter.llm.adapter import (
    LLMResponse,
    Message,
    TokenUsage,
    ToolCall,
    ToolDefinition,
)

logger = logging.getLogger(__name__)


class OpenAICompatAdapter:
    """Adapter for any OpenAI-compatible API (OpenAI, Together, Groq, local vLLM, etc.)."""

    def __init__(
        self,
        base_url: str = "https://api.openai.com/v1",
        api_key: str = "",
        model: str = "gpt-4o-mini",
        tier: Literal["local", "cheap", "sota"] = "cheap",
        timeout: float = 120.0,
    ):
        self._base_url = base_url.rstrip("/")
        self._api_key = api_key
        self._model = model
        self._tier = tier
        self._client = httpx.AsyncClient(
            base_url=self._base_url,
            headers={"Authorization": f"Bearer {api_key}"},
            timeout=timeout,
        )

    @property
    def model_id(self) -> str:
        return self._model

    @property
    def tier(self) -> Literal["local", "cheap", "sota"]:
        return self._tier

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
            "temperature": temperature,
            "max_tokens": max_tokens,
        }

        if tools:
            payload["tools"] = [t.to_dict() for t in tools]

        start = time.monotonic()
        response = await self._client.post("/chat/completions", json=payload)
        latency = (time.monotonic() - start) * 1000

        response.raise_for_status()
        data = response.json()

        choice = data["choices"][0]
        message = choice["message"]
        content = message.get("content", "") or ""

        tool_calls = []
        for tc in message.get("tool_calls", []):
            args = tc["function"].get("arguments", "{}")
            if isinstance(args, str):
                args = json.loads(args)
            tool_calls.append(
                ToolCall(
                    id=tc["id"],
                    name=tc["function"]["name"],
                    arguments=args,
                )
            )

        usage_data = data.get("usage", {})
        usage = TokenUsage(
            prompt_tokens=usage_data.get("prompt_tokens", 0),
            completion_tokens=usage_data.get("completion_tokens", 0),
        )

        return LLMResponse(
            content=content,
            tool_calls=tool_calls,
            usage=usage,
            latency_ms=latency,
        )

    async def __aenter__(self) -> OpenAICompatAdapter:
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
