from __future__ import annotations

import json

import redis.asyncio as aioredis

from app.models.schemas import Message
from app.conversation.store import ConversationStore


class RedisConversationStore(ConversationStore):
    """Redis-backed conversation store with TTL-based session expiry.

    Each session is stored as a JSON array under key ``session:<session_id>``.
    The TTL is refreshed on every append so active conversations don't expire.
    """

    def __init__(self, url: str, ttl: int = 86400) -> None:
        self._url = url
        self._ttl = ttl
        self._client: aioredis.Redis | None = None

    async def _get_client(self) -> aioredis.Redis:
        if self._client is None:
            self._client = aioredis.from_url(self._url, decode_responses=True)
        return self._client

    async def get(self, session_id: str) -> list[Message]:
        r = await self._get_client()
        raw = await r.get(f"session:{session_id}")
        if not raw:
            return []
        return [Message(**m) for m in json.loads(raw)]

    async def append(self, session_id: str, messages: list[Message]) -> None:
        r = await self._get_client()
        key = f"session:{session_id}"
        existing = await self.get(session_id)
        updated = existing + messages
        await r.setex(key, self._ttl, json.dumps([m.model_dump() for m in updated]))

    async def delete(self, session_id: str) -> None:
        r = await self._get_client()
        await r.delete(f"session:{session_id}")
