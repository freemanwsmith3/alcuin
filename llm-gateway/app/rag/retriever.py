"""Vector similarity search against pgvector."""
from __future__ import annotations

import logging
import time
from dataclasses import dataclass

from app.rag import db
from app.rag.embedder import embed_query

logger = logging.getLogger(__name__)


@dataclass
class RetrievedChunk:
    chunk_id: str
    document_id: str
    filename: str
    chunk_index: int
    content: str
    score: float          # cosine similarity: 1.0 = identical, 0.0 = unrelated


async def retrieve(
    query: str,
    top_k: int = 5,
    document_ids: list[str] | None = None,
    min_score: float = 0.0,
    user_id: str | None = None,
) -> list[RetrievedChunk]:
    """
    Embed query, search pgvector for nearest chunks, return ranked results.

    document_ids: optional filter — only search within these documents.
    min_score: discard chunks below this cosine similarity threshold.
    user_id: restrict search to documents owned by this user.
    """
    t0 = time.perf_counter()
    query_embedding = await embed_query(query)
    embed_ms = round((time.perf_counter() - t0) * 1000, 2)

    embedding_str = "[" + ",".join(str(x) for x in query_embedding) + "]"

    t1 = time.perf_counter()
    async with db.acquire() as conn:
        if document_ids:
            rows = await conn.fetch(
                """
                SELECT
                    c.id,
                    c.document_id,
                    d.filename,
                    c.chunk_index,
                    c.content,
                    1 - (c.embedding <=> $1::vector) AS score
                FROM chunks c
                JOIN documents d ON d.id = c.document_id
                WHERE c.document_id = ANY($2::uuid[])
                  AND d.status = 'ready'
                  AND ($5::uuid IS NULL OR d.user_id = $5::uuid)
                  AND 1 - (c.embedding <=> $1::vector) >= $3
                ORDER BY c.embedding <=> $1::vector
                LIMIT $4
                """,
                embedding_str,
                document_ids,
                min_score,
                top_k,
                user_id,
            )
        else:
            rows = await conn.fetch(
                """
                SELECT
                    c.id,
                    c.document_id,
                    d.filename,
                    c.chunk_index,
                    c.content,
                    1 - (c.embedding <=> $1::vector) AS score
                FROM chunks c
                JOIN documents d ON d.id = c.document_id
                WHERE d.status = 'ready'
                  AND ($4::uuid IS NULL OR d.user_id = $4::uuid)
                  AND 1 - (c.embedding <=> $1::vector) >= $2
                ORDER BY c.embedding <=> $1::vector
                LIMIT $3
                """,
                embedding_str,
                min_score,
                top_k,
                user_id,
            )
    search_ms = round((time.perf_counter() - t1) * 1000, 2)

    logger.info(
        "rag_query",
        extra={
            "query": query[:100],
            "top_k": top_k,
            "results": len(rows),
            "embed_ms": embed_ms,
            "search_ms": search_ms,
            "document_ids": document_ids,
        },
    )

    return [
        RetrievedChunk(
            chunk_id=str(row["id"]),
            document_id=str(row["document_id"]),
            filename=row["filename"],
            chunk_index=row["chunk_index"],
            content=row["content"],
            score=float(row["score"]),
        )
        for row in rows
    ]
