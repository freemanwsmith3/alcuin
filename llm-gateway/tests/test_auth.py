"""Tests for AuthMiddleware."""
from __future__ import annotations

import pytest
from httpx import AsyncClient

from tests.conftest import CHAT_PAYLOAD


async def test_no_key_configured_returns_403(client: AsyncClient, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("GATEWAY_API_KEY", raising=False)
    resp = await client.post("/api/v1/chat", json=CHAT_PAYLOAD)
    assert resp.status_code == 403


async def test_wrong_key_returns_401(client: AsyncClient, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("GATEWAY_API_KEY", "correct-key")
    resp = await client.post(
        "/api/v1/chat",
        json=CHAT_PAYLOAD,
        headers={"X-API-Key": "wrong-key"},
    )
    assert resp.status_code == 401


async def test_missing_key_returns_401(client: AsyncClient, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("GATEWAY_API_KEY", "correct-key")
    resp = await client.post("/api/v1/chat", json=CHAT_PAYLOAD)
    assert resp.status_code == 401


async def test_correct_key_returns_200(authed_client: AsyncClient) -> None:
    resp = await authed_client.post("/api/v1/chat", json=CHAT_PAYLOAD)
    assert resp.status_code == 200


async def test_health_endpoint_no_auth_required(client: AsyncClient, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("GATEWAY_API_KEY", "secret")
    resp = await client.get("/health")
    assert resp.status_code == 200
