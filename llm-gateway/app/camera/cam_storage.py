"""Upload camera snapshots to Azure Blob Storage."""
from __future__ import annotations

from datetime import datetime, timezone

from app.rag.storage import _client, _container


def upload_snapshot(image_bytes: bytes, user_id: str) -> str:
    """Upload a JPEG snapshot and return its public blob URL."""
    ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    key = f"camera/{user_id}/{ts}.jpg"
    client = _client()
    blob = client.get_blob_client(container=_container(), blob=key)
    blob.upload_blob(image_bytes, overwrite=True)
    return blob.url
