from __future__ import annotations

from collections.abc import AsyncIterator
from unittest.mock import patch

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from app.main import app
from app.models.schemas import LLMResponse, Message
from app.providers.base import LLMProvider


class FakeProvider(LLMProvider):
    """Deterministic stand-in that never hits real APIs."""

    def __init__(self, name: str = "fake") -> None:
        self._name = name

    @property
    def provider_name(self) -> str:
        return self._name

    async def complete(self, messages, config) -> LLMResponse:
        return LLMResponse(
            content="hello from fake",
            model=config.model,
            provider=self._name,
            input_tokens=10,
            output_tokens=5,
        )

    async def stream(self, messages, config) -> AsyncIterator[str]:
        for chunk in ["hello ", "from ", "fake"]:
            yield chunk


@pytest.fixture
def fake_provider() -> FakeProvider:
    return FakeProvider()


def _clear_caches() -> None:
    import app.api.routes as routes
    routes.get_store.cache_clear()
    routes.get_anthropic.cache_clear()
    routes.get_openai.cache_clear()


@pytest_asyncio.fixture
async def client(fake_provider: FakeProvider) -> AsyncIterator[AsyncClient]:
    import app.api.routes as routes
    _clear_caches()
    with (
        patch.object(routes, "get_anthropic", return_value=fake_provider),
        patch.object(routes, "get_openai", return_value=fake_provider),
    ):
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as ac:
            yield ac
    _clear_caches()


@pytest_asyncio.fixture
async def authed_client(
    fake_provider: FakeProvider, monkeypatch: pytest.MonkeyPatch
) -> AsyncIterator[AsyncClient]:
    import app.api.routes as routes
    monkeypatch.setenv("GATEWAY_API_KEY", "test-secret")
    _clear_caches()
    with (
        patch.object(routes, "get_anthropic", return_value=fake_provider),
        patch.object(routes, "get_openai", return_value=fake_provider),
    ):
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
            headers={"X-API-Key": "test-secret"},
        ) as ac:
            yield ac
    _clear_caches()


CHAT_PAYLOAD = {
    "messages": [{"role": "user", "content": "hi"}],
    "config": {"model": "claude-haiku-4-5-20251001"},
}
