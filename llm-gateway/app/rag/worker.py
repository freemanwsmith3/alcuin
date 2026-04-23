"""arq worker: processes uploaded PDFs into chunks + embeddings, and periodic camera captures."""
from __future__ import annotations

import asyncio
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


async def camera_capture(ctx: dict) -> None:
    """Periodic job: fetch a camera snapshot, analyze it, and store the reading.

    Only runs when CAMERA_USER_ID is set in the environment.
    Interval controlled by CAMERA_CAPTURE_MINUTES (default: 30).
    """
    user_id = os.environ.get("CAMERA_USER_ID")
    if not user_id:
        return

    question = os.environ.get(
        "CAMERA_ANALYSIS_QUESTION",
        "Describe what you see in this image.",
    )
    store_images = os.environ.get("CAMERA_STORE_IMAGES", "false").lower() == "true"

    from app.camera import analyzer, cam_storage

    try:
        image = await asyncio.to_thread(analyzer.fetch_snapshot)
        result = await asyncio.to_thread(analyzer.analyze, image, question)
    except Exception as exc:
        logger.error("camera_capture_failed", extra={"error": str(exc)})
        return

    image_url = None
    if store_images:
        try:
            image_url = await asyncio.to_thread(cam_storage.upload_snapshot, image, user_id)
        except Exception as exc:
            logger.warning("camera_store_image_failed", extra={"error": str(exc)})

    measurement = result.get("measurement") or {}
    pool = await db.get_pool()
    async with pool.acquire() as conn:
        await conn.execute(
            """
            INSERT INTO camera_readings (user_id, value, unit, label, notes, image_url)
            VALUES ($1, $2, $3, $4, $5, $6)
            """,
            user_id,
            measurement.get("value"),
            measurement.get("unit"),
            measurement.get("label"),
            measurement.get("notes") or result.get("description"),
            image_url,
        )
    logger.info("camera_capture_complete", extra={"user_id": user_id[:8]})


async def startup(ctx: dict) -> None:
    await db.get_pool()


async def shutdown(ctx: dict) -> None:
    await db.close_pool()


_capture_minutes = int(os.environ.get("CAMERA_CAPTURE_MINUTES", "30"))

class WorkerSettings:
    functions = [process_document, camera_capture]
    cron_jobs = [cron(camera_capture, minute={i for i in range(0, 60, _capture_minutes)})]
    redis_settings = RedisSettings.from_dsn(
        os.environ.get("REDIS_URL", "redis://localhost:6379")
    )
    on_startup = startup
    on_shutdown = shutdown
