"""OpenAI embeddings for text chunks."""
from __future__ import annotations

import asyncio
import os

from openai import AsyncOpenAI

EMBEDDING_MODEL = "text-embedding-3-small"
EMBEDDING_DIM = 1536
_BATCH_SIZE = 100   # OpenAI allows up to 2048 inputs per request


_client: AsyncOpenAI | None = None


def _get_client() -> AsyncOpenAI:
    global _client
    if _client is None:
        _client = AsyncOpenAI(api_key=os.environ["OPENAI_API_KEY"])
    return _client


async def embed_texts(texts: list[str]) -> list[list[float]]:
    """Return embeddings for a list of texts, batched to respect API limits."""
    client = _get_client()
    all_embeddings: list[list[float]] = []

    for i in range(0, len(texts), _BATCH_SIZE):
        batch = texts[i : i + _BATCH_SIZE]
        response = await client.embeddings.create(
            model=EMBEDDING_MODEL,
            input=batch,
        )
        all_embeddings.extend(item.embedding for item in response.data)

    return all_embeddings


async def embed_query(text: str) -> list[float]:
    """Return a single embedding for a query string."""
    embeddings = await embed_texts([text])
    return embeddings[0]
