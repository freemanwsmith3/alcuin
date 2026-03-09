"""Tests for InMemoryConversationStore."""
from __future__ import annotations

import pytest

from app.conversation.store import InMemoryConversationStore
from app.models.schemas import Message


@pytest.fixture
def store() -> InMemoryConversationStore:
    return InMemoryConversationStore()


async def test_get_missing_session_returns_empty(store: InMemoryConversationStore) -> None:
    result = await store.get("nonexistent")
    assert result == []


async def test_append_then_get_returns_messages(store: InMemoryConversationStore) -> None:
    msgs = [Message(role="user", content="hi")]
    await store.append("s1", msgs)
    result = await store.get("s1")
    assert result == msgs


async def test_append_twice_accumulates(store: InMemoryConversationStore) -> None:
    m1 = [Message(role="user", content="hello")]
    m2 = [Message(role="assistant", content="world")]
    await store.append("s1", m1)
    await store.append("s1", m2)
    result = await store.get("s1")
    assert len(result) == 2
    assert result[0].content == "hello"
    assert result[1].content == "world"


async def test_get_returns_copy_not_reference(store: InMemoryConversationStore) -> None:
    msgs = [Message(role="user", content="original")]
    await store.append("s1", msgs)
    result = await store.get("s1")
    result.append(Message(role="assistant", content="mutated"))
    assert len(await store.get("s1")) == 1


async def test_delete_removes_session(store: InMemoryConversationStore) -> None:
    await store.append("s1", [Message(role="user", content="hi")])
    await store.delete("s1")
    assert await store.get("s1") == []


async def test_delete_nonexistent_is_noop(store: InMemoryConversationStore) -> None:
    await store.delete("does-not-exist")  # should not raise


async def test_sessions_are_independent(store: InMemoryConversationStore) -> None:
    await store.append("s1", [Message(role="user", content="s1")])
    await store.append("s2", [Message(role="user", content="s2")])
    assert (await store.get("s1"))[0].content == "s1"
    assert (await store.get("s2"))[0].content == "s2"
