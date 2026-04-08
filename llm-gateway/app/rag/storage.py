"""Azure Blob Storage client for storing and retrieving raw PDF files."""
from __future__ import annotations

import os

from azure.storage.blob import BlobServiceClient


def _client() -> BlobServiceClient:
    return BlobServiceClient.from_connection_string(
        os.environ["AZURE_STORAGE_CONNECTION_STRING"]
    )


def _container() -> str:
    return os.environ.get("AZURE_STORAGE_CONTAINER", "documents")


def ensure_bucket() -> None:
    """No-op for Azure — container is created manually in the portal."""
    pass


def upload(object_key: str, data: bytes, content_type: str = "application/pdf") -> None:
    client = _client()
    blob = client.get_blob_client(container=_container(), blob=object_key)
    blob.upload_blob(data, overwrite=True, content_settings=None)


def download(object_key: str) -> bytes:
    client = _client()
    blob = client.get_blob_client(container=_container(), blob=object_key)
    return blob.download_blob().readall()
