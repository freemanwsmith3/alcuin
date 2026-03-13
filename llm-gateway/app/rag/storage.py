"""MinIO client for storing and retrieving raw PDF files."""
from __future__ import annotations

import io
import os

from minio import Minio
from minio.error import S3Error


def _client() -> Minio:
    return Minio(
        endpoint=os.environ["MINIO_ENDPOINT"],
        access_key=os.environ["MINIO_ACCESS_KEY"],
        secret_key=os.environ["MINIO_SECRET_KEY"],
        secure=False,
    )


def _bucket() -> str:
    return os.environ.get("MINIO_BUCKET", "documents")


def ensure_bucket() -> None:
    """Create the bucket if it doesn't exist. Called at startup."""
    client = _client()
    bucket = _bucket()
    if not client.bucket_exists(bucket):
        client.make_bucket(bucket)


def upload(object_key: str, data: bytes, content_type: str = "application/pdf") -> None:
    client = _client()
    client.put_object(
        bucket_name=_bucket(),
        object_name=object_key,
        data=io.BytesIO(data),
        length=len(data),
        content_type=content_type,
    )


def download(object_key: str) -> bytes:
    client = _client()
    response = client.get_object(bucket_name=_bucket(), object_name=object_key)
    try:
        return response.read()
    finally:
        response.close()
        response.release_conn()
