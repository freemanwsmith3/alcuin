"""RAG API routes: document upload, status, and retrieval."""
from __future__ import annotations

import logging
import os
import uuid
from typing import Optional

from arq import create_pool as arq_create_pool
from arq.connections import RedisSettings
from fastapi import APIRouter, HTTPException, UploadFile, File
from pydantic import BaseModel, Field

from app.rag import db, storage
from app.rag.retriever import retrieve

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/rag", tags=["rag"])

_MAX_FILE_SIZE = 200 * 1024 * 1024  # 200 MB


async def _enqueue(document_id: str) -> None:
    redis = await arq_create_pool(
        RedisSettings.from_dsn(os.environ.get("REDIS_URL", "redis://localhost:6379"))
    )
    await redis.enqueue_job("process_document", document_id)
    await redis.aclose()


@router.post("/documents", status_code=202)
async def upload_document(file: UploadFile = File(...)) -> dict:
    """Upload a PDF. Returns immediately with a document_id to poll for status."""
    if file.content_type not in ("application/pdf", "application/octet-stream"):
        raise HTTPException(status_code=400, detail="only PDF files are accepted")

    data = await file.read()
    if len(data) > _MAX_FILE_SIZE:
        raise HTTPException(status_code=413, detail="file exceeds 200 MB limit")
    if not data:
        raise HTTPException(status_code=400, detail="empty file")

    document_id = str(uuid.uuid4())
    filename = file.filename or "upload.pdf"
    storage_key = f"documents/{document_id}/{filename}"

    # Store raw PDF in MinIO
    try:
        storage.ensure_bucket()
        storage.upload(storage_key, data, content_type="application/pdf")
    except Exception as exc:
        logger.exception("minio upload failed")
        raise HTTPException(status_code=502, detail="storage error") from exc

    # Insert document row in Postgres
    async with db.acquire() as conn:
        await conn.execute(
            """
            INSERT INTO documents (id, filename, content_type, size_bytes, storage_key, status)
            VALUES ($1, $2, 'application/pdf', $3, $4, 'pending')
            """,
            document_id,
            filename,
            len(data),
            storage_key,
        )

    # Enqueue arq job for async processing
    await _enqueue(document_id)

    return {
        "document_id": document_id,
        "filename": filename,
        "size_bytes": len(data),
        "status": "pending",
    }


@router.get("/documents/{document_id}")
async def get_document(document_id: str) -> dict:
    """Poll processing status for an uploaded document."""
    async with db.acquire() as conn:
        row = await conn.fetchrow(
            """
            SELECT id, filename, size_bytes, status, error_message, chunk_count, created_at
            FROM documents WHERE id = $1
            """,
            document_id,
        )

    if row is None:
        raise HTTPException(status_code=404, detail="document not found")

    return {
        "document_id": str(row["id"]),
        "filename": row["filename"],
        "size_bytes": row["size_bytes"],
        "status": row["status"],
        "chunk_count": row["chunk_count"],
        "error_message": row["error_message"],
        "created_at": row["created_at"].isoformat(),
    }


# ---------------------------------------------------------------------------
# Retrieval
# ---------------------------------------------------------------------------

class QueryRequest(BaseModel):
    query: str = Field(min_length=1, max_length=2000)
    document_ids: Optional[list[str]] = Field(
        default=None,
        description="Limit search to these document IDs. Omit to search all documents.",
    )
    top_k: int = Field(default=5, ge=1, le=20)
    min_score: float = Field(default=0.0, ge=0.0, le=1.0)


@router.post("/query")
async def query_documents(request: QueryRequest) -> dict:
    """
    Semantic search across ingested documents.
    Returns the top_k most relevant chunks with similarity scores.
    """
    try:
        chunks = await retrieve(
            query=request.query,
            top_k=request.top_k,
            document_ids=request.document_ids,
            min_score=request.min_score,
        )
    except Exception as exc:
        logger.exception("retrieval failed")
        raise HTTPException(status_code=502, detail=str(exc))

    return {
        "query": request.query,
        "results": [
            {
                "chunk_id": c.chunk_id,
                "document_id": c.document_id,
                "filename": c.filename,
                "chunk_index": c.chunk_index,
                "content": c.content,
                "score": round(c.score, 4),
            }
            for c in chunks
        ],
    }
