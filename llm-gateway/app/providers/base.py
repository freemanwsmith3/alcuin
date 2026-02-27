from __future__ import annotations

from abc import ABC, abstractmethod
from typing import AsyncIterator

from app.models.schemas import LLMResponse, Message, ModelConfig


class LLMProvider(ABC):
    """Abstract base class for all LLM provider implementations.

    Concrete providers translate internal schemas to their SDK's format
    and back. Routes only interact with this interface.
    """

    @property
    @abstractmethod
    def provider_name(self) -> str:
        """Stable identifier for this provider (e.g. 'anthropic', 'openai')."""
        ...

    @abstractmethod
    async def complete(
        self,
        messages: list[Message],
        config: ModelConfig,
    ) -> LLMResponse:
        """Return a single, complete response for the given conversation."""
        ...

    @abstractmethod
    def stream(
        self,
        messages: list[Message],
        config: ModelConfig,
    ) -> AsyncIterator[str]:
        """Yield response text chunks as they arrive from the provider.

        Declared as a plain method (not async def) so subclasses can be
        implemented as async generators and consumed directly with
        ``async for chunk in provider.stream(...):``.
        """
        ...
