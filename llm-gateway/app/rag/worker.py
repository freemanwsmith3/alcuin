"""arq worker: processes uploaded PDFs into chunks + embeddings."""
from __future__ import annotations

import logging
import os

from arq import cron
from arq.connections import RedisSettings

from app.rag import db, storage
from app.rag.chunker import pdf_to_chunks
from app.rag.embedder import embed_texts

logger = logging.getLogger(__name__)


async def process_document(ctx: dict, document_id: str) -> None:
    """
    arq job: download PDF from MinIO, chunk, embed, store in pgvector.
    Runs in the worker container, not the gateway.
    """
    pool = await db.get_pool()

    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            "SELECT storage_key, filename FROM documents WHERE id = $1",
            document_id,
        )
        if row is None:
            logger.error("document not found", extra={"document_id": document_id})
            return

        await conn.execute(
            "UPDATE documents SET status = 'processing', updated_at = NOW() WHERE id = $1",
            document_id,
        )

    try:
        logger.info("downloading pdf", extra={"document_id": document_id})
        pdf_bytes = storage.download(row["storage_key"])

        logger.info("chunking pdf", extra={"document_id": document_id})
        chunks = pdf_to_chunks(pdf_bytes)

        if not chunks:
            raise ValueError("no text extracted from PDF")

        logger.info(
            "embedding chunks",
            extra={"document_id": document_id, "chunk_count": len(chunks)},
        )
        embeddings = await embed_texts([c.content for c in chunks])

        async with pool.acquire() as conn:
            async with conn.transaction():
                await conn.executemany(
                    """
                    INSERT INTO chunks (document_id, chunk_index, content, token_count, embedding)
                    VALUES ($1, $2, $3, $4, $5::vector)
                    """,
                    [
                        (document_id, c.index, c.content, c.token_count, str(emb))
                        for c, emb in zip(chunks, embeddings)
                    ],
                )
                await conn.execute(
                    """
                    UPDATE documents
                    SET status = 'ready', chunk_count = $2, updated_at = NOW()
                    WHERE id = $1
                    """,
                    document_id,
                    len(chunks),
                )

        logger.info(
            "document ready",
            extra={"document_id": document_id, "chunk_count": len(chunks)},
        )

    except Exception as exc:
        logger.exception("failed to process document", extra={"document_id": document_id})
        async with pool.acquire() as conn:
            await conn.execute(
                "UPDATE documents SET status = 'failed', error_message = $2, updated_at = NOW() WHERE id = $1",
                document_id,
                str(exc),
            )


async def startup(ctx: dict) -> None:
    await db.get_pool()


async def shutdown(ctx: dict) -> None:
    await db.close_pool()


class WorkerSettings:
    functions = [process_document]
    redis_settings = RedisSettings.from_dsn(
        os.environ.get("REDIS_URL", "redis://localhost:6379")
    )
    on_startup = startup
    on_shutdown = shutdown
