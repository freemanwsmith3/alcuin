"""Fetch camera snapshots and analyze with Claude vision."""
from __future__ import annotations

import base64
import json
import logging
import os

import httpx
from anthropic import Anthropic

logger = logging.getLogger(__name__)

_client = Anthropic()
_CAMERA_SNAPSHOT_URL = os.environ.get("CAMERA_SNAPSHOT_URL", "")

_SYSTEM = """\
You analyze images from a camera.
When asked to measure or estimate something numeric, respond with ONLY valid JSON:
{"value": <number>, "unit": "<unit>", "label": "<short label>", "notes": "<observations>"}
Otherwise describe what you see in 1-2 sentences.
"""


def fetch_snapshot() -> bytes:
    if not _CAMERA_SNAPSHOT_URL:
        raise RuntimeError("CAMERA_SNAPSHOT_URL not configured")
    resp = httpx.get(_CAMERA_SNAPSHOT_URL, timeout=10)
    resp.raise_for_status()
    return resp.content


def analyze(image_bytes: bytes, question: str) -> dict:
    """Send image to Claude vision and return a structured result."""
    b64 = base64.standard_b64encode(image_bytes).decode()
    response = _client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=512,
        system=_SYSTEM,
        messages=[{
            "role": "user",
            "content": [
                {"type": "image", "source": {"type": "base64", "media_type": "image/jpeg", "data": b64}},
                {"type": "text", "text": question},
            ],
        }],
    )
    text = response.content[0].text.strip()
    logger.info("camera_analysis_done", extra={"question": question[:80]})

    try:
        data = json.loads(text)
        if isinstance(data, dict):
            return {"success": True, "measurement": data, "description": data.get("notes", "")}
    except (json.JSONDecodeError, ValueError):
        pass

    return {"success": True, "description": text}
