"""Camera snapshot proxy and time-series readings API."""
from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import Response

from app.auth.dependencies import CurrentUser, get_current_user
from app.camera import analyzer
from app.camera import cam_storage
from app.rag import db

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/camera", tags=["camera"])


@router.get("/live")
async def live() -> Response:
    """Public unauthenticated endpoint — returns the latest JPEG frame."""
    try:
        image = analyzer.fetch_snapshot()
    except Exception as e:
        logger.error("camera_live_error", extra={"error": str(e)})
        raise HTTPException(status_code=502, detail="Could not reach camera")
    return Response(content=image, media_type="image/jpeg")


@router.get("/snapshot")
async def snapshot(user: CurrentUser = Depends(get_current_user)) -> Response:
    """Proxy the latest JPEG frame from the camera."""
    try:
        image = analyzer.fetch_snapshot()
    except Exception as e:
        logger.error("camera_snapshot_error", extra={"error": str(e)})
        raise HTTPException(status_code=502, detail="Could not reach camera")
    return Response(content=image, media_type="image/jpeg")


@router.post("/analyze")
async def analyze(
    question: str = Query(default="Describe what you see"),
    store_image: bool = Query(default=False),
    user: CurrentUser = Depends(get_current_user),
) -> dict:
    """Capture a snapshot, analyze with Claude vision, and store the reading."""
    try:
        image = analyzer.fetch_snapshot()
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Could not reach camera: {e}")

    result = analyzer.analyze(image, question)

    image_url = None
    if store_image:
        try:
            image_url = cam_storage.upload_snapshot(image, user.id)
        except Exception as e:
            logger.warning("camera_image_upload_failed", extra={"error": str(e)})

    measurement = result.get("measurement") or {}
    pool = await db.get_pool()
    async with pool.acquire() as conn:
        await conn.execute(
            """
            INSERT INTO camera_readings (user_id, value, unit, label, notes, image_url)
            VALUES ($1, $2, $3, $4, $5, $6)
            """,
            user.id,
            measurement.get("value"),
            measurement.get("unit"),
            measurement.get("label"),
            measurement.get("notes") or result.get("description"),
            image_url,
        )

    return {"result": result, "image_url": image_url}


@router.get("/readings")
async def readings(
    limit: int = Query(default=200, le=1000),
    user: CurrentUser = Depends(get_current_user),
) -> dict:
    """Return time-series readings ordered oldest-first for charting."""
    pool = await db.get_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            """
            SELECT id, captured_at, value, unit, label, notes, image_url
            FROM camera_readings
            WHERE user_id = $1
            ORDER BY captured_at ASC
            LIMIT $2
            """,
            user.id,
            limit,
        )
    return {
        "readings": [
            {
                "id": str(r["id"]),
                "captured_at": r["captured_at"].isoformat(),
                "value": r["value"],
                "unit": r["unit"],
                "label": r["label"],
                "notes": r["notes"],
                "image_url": r["image_url"],
            }
            for r in rows
        ]
    }
