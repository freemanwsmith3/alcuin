from __future__ import annotations

import uuid
from abc import ABC, abstractmethod

from app.models.schemas import Message


class ConversationStore(ABC):
    """Interface for conversation persistence.

    Swap this out for a Redis or database-backed implementation
    without touching any route logic.
    """

    @abstractmethod
    async def get(self, session_id: str) -> list[Message]:
        """Return all stored messages for a session, or [] if not found."""
        ...

    @abstractmethod
    async def append(self, session_id: str, messages: list[Message]) -> None:
        """Append messages to a session, creating it if it doesn't exist."""
        ...

    @abstractmethod
    async def delete(self, session_id: str) -> None:
        """Remove a session entirely."""
        ...


class InMemoryConversationStore(ConversationStore):
    """Simple in-memory store. Data is lost on server restart."""

    def __init__(self) -> None:
        self._sessions: dict[str, list[Message]] = {}

    async def get(self, session_id: str) -> list[Message]:
        return list(self._sessions.get(session_id, []))

    async def append(self, session_id: str, messages: list[Message]) -> None:
        if session_id not in self._sessions:
            self._sessions[session_id] = []
        self._sessions[session_id].extend(messages)

    async def delete(self, session_id: str) -> None:
        self._sessions.pop(session_id, None)


def new_session_id() -> str:
    return str(uuid.uuid4())
