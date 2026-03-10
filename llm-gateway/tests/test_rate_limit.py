"""Tests for RateLimitMiddleware."""
from __future__ import annotations

from unittest.mock import patch

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from app.main import app
from tests.conftest import CHAT_PAYLOAD, FakeProvider, _clear_caches


@pytest_asyncio.fixture
async def limited_client(monkeypatch: pytest.MonkeyPatch) -> AsyncClient:
    """Authenticated client with a very low rate limit (3 rpm) for fast testing."""
    import app.api.routes as routes
    import app.middleware.rate_limit as rl_module

    monkeypatch.setenv("GATEWAY_API_KEY", "test-secret")
    _clear_caches()

    fake = FakeProvider()
    # Patch the middleware's rpm on the already-constructed app instance
    for middleware in app.middleware_stack.__class__.__mro__:
        pass  # we patch at the module level instead

    # Re-create the app with a low limit by patching the env var before import
    with (
        patch.object(routes, "get_anthropic", return_value=fake),
        patch.object(routes, "get_openai", return_value=fake),
    ):
        # Directly patch the middleware instance on the app
        for layer in app.middleware_stack.__dict__.get("app", app).__dict__.values():
            pass

        # Simplest approach: patch the _rpm attribute on the live middleware instance
        for key, val in app.__dict__.items():
            pass

        async with AsyncClient(
            transport=ASGITransport(app=_make_limited_app(fake, monkeypatch)),
            base_url="http://test",
            headers={"X-API-Key": "test-secret"},
        ) as ac:
            yield ac
    _clear_caches()


def _make_limited_app(fake_provider: FakeProvider, monkeypatch: pytest.MonkeyPatch):
    """Build a fresh FastAPI app with a 3 rpm rate limit for testing."""
    import os
    from unittest.mock import patch as _patch

    from fastapi import FastAPI
    from fastapi.staticfiles import StaticFiles

    from app.api.routes import router as api_router
    from app.middleware.auth import AuthMiddleware
    from app.middleware.rate_limit import RateLimitMiddleware
    import app.api.routes as routes

    _clear_caches()

    test_app = FastAPI()
    test_app.add_middleware(AuthMiddleware)
    test_app.add_middleware(RateLimitMiddleware, requests_per_minute=3)
    test_app.include_router(api_router, prefix="/api/v1")

    @test_app.get("/health")
    async def health():
        return {"status": "ok"}

    return test_app


@pytest_asyncio.fixture
async def rate_limited_client(monkeypatch: pytest.MonkeyPatch):
    """Client against a fresh app capped at 3 requests/minute."""
    import app.api.routes as routes

    monkeypatch.setenv("GATEWAY_API_KEY", "test-secret")
    _clear_caches()

    fake = FakeProvider()
    test_app = _make_limited_app(fake, monkeypatch)

    with (
        patch.object(routes, "get_anthropic", return_value=fake),
        patch.object(routes, "get_openai", return_value=fake),
    ):
        async with AsyncClient(
            transport=ASGITransport(app=test_app),
            base_url="http://test",
            headers={"X-API-Key": "test-secret"},
        ) as ac:
            yield ac
    _clear_caches()


async def test_requests_under_limit_pass(rate_limited_client: AsyncClient) -> None:
    for _ in range(3):
        resp = await rate_limited_client.post("/api/v1/chat", json=CHAT_PAYLOAD)
        assert resp.status_code == 200


async def test_request_over_limit_returns_429(rate_limited_client: AsyncClient) -> None:
    for _ in range(3):
        await rate_limited_client.post("/api/v1/chat", json=CHAT_PAYLOAD)
    resp = await rate_limited_client.post("/api/v1/chat", json=CHAT_PAYLOAD)
    assert resp.status_code == 429
    assert resp.json()["detail"] == "rate limit exceeded"


async def test_429_has_retry_after_header(rate_limited_client: AsyncClient) -> None:
    for _ in range(3):
        await rate_limited_client.post("/api/v1/chat", json=CHAT_PAYLOAD)
    resp = await rate_limited_client.post("/api/v1/chat", json=CHAT_PAYLOAD)
    assert resp.status_code == 429
    assert "retry-after" in resp.headers


async def test_non_api_paths_not_rate_limited(rate_limited_client: AsyncClient) -> None:
    for _ in range(5):
        resp = await rate_limited_client.get("/health")
        assert resp.status_code == 200
