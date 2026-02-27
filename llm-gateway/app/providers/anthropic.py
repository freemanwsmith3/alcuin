from __future__ import annotations

import os
from typing import AsyncIterator

import anthropic

from app.models.schemas import LLMResponse, Message, ModelConfig
from app.providers.base import LLMProvider


class AnthropicProvider(LLMProvider):
    """Anthropic Claude provider using the official async SDK."""

    def __init__(self, api_key: str | None = None) -> None:
        self._client = anthropic.AsyncAnthropic(
            api_key=api_key or os.environ["ANTHROPIC_API_KEY"]
        )

    @property
    def provider_name(self) -> str:
        return "anthropic"

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _translate_messages(
        self, messages: list[Message]
    ) -> tuple[str | None, list[dict]]:
        """Split out the system prompt and convert to Anthropic's format.

        Anthropic takes system content as a top-level parameter, not as
        a message in the array. If multiple system messages are present,
        their content is joined — the API only accepts one system block.
        """
        system_parts: list[str] = []
        api_messages: list[dict] = []

        for msg in messages:
            if msg.role == "system":
                system_parts.append(msg.content)
            else:
                api_messages.append({"role": msg.role, "content": msg.content})

        if not api_messages:
            raise ValueError("At least one user or assistant message is required.")

        system = "\n\n".join(system_parts) if system_parts else None
        return system, api_messages

    def _build_kwargs(self, config: ModelConfig, system: str | None, messages: list[dict]) -> dict:
        kwargs: dict = {
            "model": config.model,
            "max_tokens": config.max_tokens or 1024,
            "messages": messages,
        }
        if system is not None:
            kwargs["system"] = system
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
        system, api_messages = self._translate_messages(messages)
        kwargs = self._build_kwargs(config, system, api_messages)

        response = await self._client.messages.create(**kwargs)

        return LLMResponse(
            content=response.content[0].text,
            model=response.model,
            provider=self.provider_name,
            input_tokens=response.usage.input_tokens,
            output_tokens=response.usage.output_tokens,
        )

    async def stream(  # type: ignore[override]
        self,
        messages: list[Message],
        config: ModelConfig,
    ) -> AsyncIterator[str]:
        system, api_messages = self._translate_messages(messages)
        kwargs = self._build_kwargs(config, system, api_messages)

        async with self._client.messages.stream(**kwargs) as stream:
            async for text in stream.text_stream:
                yield text
