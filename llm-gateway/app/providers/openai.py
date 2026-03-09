from __future__ import annotations

import os
from typing import AsyncIterator

import openai

from app.models.schemas import LLMResponse, Message, ModelConfig
from app.providers.base import LLMProvider


class OpenAIProvider(LLMProvider):
    """OpenAI provider using the official async SDK."""

    def __init__(self, api_key: str | None = None) -> None:
        self._client = openai.AsyncOpenAI(
            api_key=api_key or os.environ["OPENAI_API_KEY"]
        )

    @property
    def provider_name(self) -> str:
        return "openai"

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _translate_messages(self, messages: list[Message]) -> list[dict]:
        """Convert internal messages to OpenAI's format.

        Unlike Anthropic, OpenAI accepts system messages directly in the
        messages array — so this is a straight conversion with no splitting.
        """
        return [{"role": msg.role, "content": msg.content} for msg in messages]

    def _build_kwargs(self, config: ModelConfig, messages: list[dict]) -> dict:
        kwargs: dict = {
            "model": config.model,
            "messages": messages,
        }
        if config.max_tokens is not None:
            kwargs["max_tokens"] = config.max_tokens
        if config.temperature is not None:
            kwargs["temperature"] = config.temperature
        if config.top_p is not None:
            kwargs["top_p"] = config.top_p
        return kwargs

    # ------------------------------------------------------------------
    # LLMProvider interface
    # ------------------------------------------------------------------

    async def complete(
        self,
        messages: list[Message],
        config: ModelConfig,
    ) -> LLMResponse:
        api_messages = self._translate_messages(messages)
        kwargs = self._build_kwargs(config, api_messages)

        response = await self._client.chat.completions.create(**kwargs)

        return LLMResponse(
            content=response.choices[0].message.content or "",
            model=response.model,
            provider=self.provider_name,
            input_tokens=response.usage.prompt_tokens if response.usage else None,
            output_tokens=response.usage.completion_tokens if response.usage else None,
        )

    async def stream(  # type: ignore[override]
        self,
        messages: list[Message],
        config: ModelConfig,
    ) -> AsyncIterator[str]:
        api_messages = self._translate_messages(messages)
        kwargs = self._build_kwargs(config, api_messages)

        async with self._client.chat.completions.stream(**kwargs) as stream:
            async for text in stream.text_stream:
                yield text