"""Tests for /api/v1/chat and /api/v1/chat/stream endpoints."""
from __future__ import annotations

import json

from httpx import AsyncClient

from tests.conftest import CHAT_PAYLOAD


async def test_chat_returns_200(authed_client: AsyncClient) -> None:
    resp = await authed_client.post("/api/v1/chat", json=CHAT_PAYLOAD)
    assert resp.status_code == 200
    data = resp.json()
    assert data["response"]["content"] == "hello from fake"
    assert data["response"]["provider"] == "fake"
    assert "session_id" in data


async def test_chat_returns_session_id(authed_client: AsyncClient) -> None:
    resp = await authed_client.post("/api/v1/chat", json=CHAT_PAYLOAD)
    session_id = resp.json()["session_id"]
    assert isinstance(session_id, str) and len(session_id) > 0


async def test_chat_conversation_continuity(authed_client: AsyncClient) -> None:
    first = await authed_client.post("/api/v1/chat", json=CHAT_PAYLOAD)
    session_id = first.json()["session_id"]

    payload_with_session = {**CHAT_PAYLOAD, "session_id": session_id}
    second = await authed_client.post("/api/v1/chat", json=payload_with_session)
    assert second.status_code == 200


async def test_chat_bad_payload_returns_422(authed_client: AsyncClient) -> None:
    resp = await authed_client.post("/api/v1/chat", json={"bad": "payload"})
    assert resp.status_code == 422


async def test_chat_empty_messages_returns_422(authed_client: AsyncClient) -> None:
    payload = {"messages": [], "config": {"model": "claude-haiku-4-5-20251001"}}
    resp = await authed_client.post("/api/v1/chat", json=payload)
    assert resp.status_code == 422


async def test_stream_returns_event_stream(authed_client: AsyncClient) -> None:
    resp = await authed_client.post("/api/v1/chat/stream", json=CHAT_PAYLOAD)
    assert resp.status_code == 200
    assert "text/event-stream" in resp.headers["content-type"]


async def test_stream_contains_done_marker(authed_client: AsyncClient) -> None:
    resp = await authed_client.post("/api/v1/chat/stream", json=CHAT_PAYLOAD)
    assert b"[DONE]" in resp.content


async def test_stream_chunks_are_valid_json(authed_client: AsyncClient) -> None:
    resp = await authed_client.post("/api/v1/chat/stream", json=CHAT_PAYLOAD)
    lines = resp.text.splitlines()
    data_lines = [l[6:] for l in lines if l.startswith("data: ") and l != "data: [DONE]"]
    for line in data_lines:
        parsed = json.loads(line)
        assert "text" in parsed or "error" in parsed


async def test_stream_session_id_in_first_chunk(authed_client: AsyncClient) -> None:
    resp = await authed_client.post("/api/v1/chat/stream", json=CHAT_PAYLOAD)
    lines = resp.text.splitlines()
    data_lines = [l[6:] for l in lines if l.startswith("data: ") and l != "data: [DONE]"]
    first = json.loads(data_lines[0])
    assert "session_id" in first
