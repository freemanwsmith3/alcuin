from __future__ import annotations

import logging
from copy import copy
from typing import AsyncIterator

from tenacity import (
    AsyncRetrying,
    RetryError,
    stop_after_attempt,
    wait_exponential,
)

from app.models.schemas import LLMResponse, Message, ModelConfig
from app.providers.base import LLMProvider

logger = logging.getLogger("llm_gateway.resilient")

# Cross-provider fallback model mapping
FALLBACK_MODEL: dict[str, str] = {
    "gpt-4o": "claude-sonnet-4-6",
    "gpt-4o-mini": "claude-haiku-4-5-20251001",
    "gpt-3.5-turbo": "claude-haiku-4-5-20251001",
    "claude-sonnet-4-6": "gpt-4o",
    "claude-haiku-4-5-20251001": "gpt-4o-mini",
    "claude-opus-4-6": "gpt-4o",
}

# HTTP-like status codes that warrant a retry
_RETRYABLE_STATUS_CODES = {429, 500, 502, 503, 504}


def _is_retryable(exc: BaseException) -> bool:
    """Return True for transient provider errors worth retrying."""
    msg = str(exc).lower()
    # Anthropic and OpenAI SDKs embed status codes in exception messages/types
    for code in _RETRYABLE_STATUS_CODES:
        if str(code) in msg:
            return True
    # Common transient error phrases
    return any(phrase in msg for phrase in ("rate limit", "overloaded", "timeout", "temporarily"))


class ResilientProvider(LLMProvider):
    """Wraps a primary provider with retry + cross-provider fallback.

    Retry strategy: up to 3 attempts on transient errors with exponential
    backoff (1s, 2s, 4s). After retries exhausted, tries the fallback
    provider with a mapped model if one exists.
    """

    def __init__(self, primary: LLMProvider, fallback: LLMProvider, model: str) -> None:
        self._primary = primary
        self._fallback = fallback
        self._model = model

    @property
    def provider_name(self) -> str:
        return self._primary.provider_name

    async def complete(self, messages: list[Message], config: ModelConfig) -> LLMResponse:
        try:
            async for attempt in AsyncRetrying(
                stop=stop_after_attempt(3),
                wait=wait_exponential(multiplier=1, min=1, max=8),
                retry=_is_retryable,
                reraise=False,
            ):
                with attempt:
                    return await self._primary.complete(messages, config)
        except RetryError:
            pass
        except Exception as exc:
            if not _is_retryable(exc):
                raise

        fallback_model = FALLBACK_MODEL.get(self._model)
        if fallback_model is None:
            raise RuntimeError(
                f"Primary provider failed and no fallback model is mapped for '{self._model}'"
            )

        logger.warning(
            "primary_provider_failed_using_fallback",
            extra={"primary": self._primary.provider_name, "fallback_model": fallback_model},
        )
        fallback_config = copy(config)
        fallback_config = config.model_copy(update={"model": fallback_model})
        return await self._fallback.complete(messages, fallback_config)

    async def stream(self, messages: list[Message], config: ModelConfig) -> AsyncIterator[str]:  # type: ignore[override]
        # For streaming we attempt once; on failure fall back without retry
        # (retrying a partial stream would duplicate output).
        try:
            async for chunk in self._primary.stream(messages, config):
                yield chunk
            return
        except Exception as exc:
            if not _is_retryable(exc):
                raise

        fallback_model = FALLBACK_MODEL.get(self._model)
        if fallback_model is None:
            raise RuntimeError(
                f"Primary provider failed and no fallback model is mapped for '{self._model}'"
            )

        logger.warning(
            "primary_stream_failed_using_fallback",
            extra={"primary": self._primary.provider_name, "fallback_model": fallback_model},
        )
        fallback_config = config.model_copy(update={"model": fallback_model})
        async for chunk in self._fallback.stream(messages, fallback_config):
            yield chunk
