import io
from pathlib import Path

from minio import Minio
from minio.error import S3Error

from core.config import settings

_client: Minio | None = None


def get_storage_client() -> Minio:
    global _client
    if _client is None:
        _client = Minio(
            settings.storage_endpoint,
            access_key=settings.storage_access_key,
            secret_key=settings.storage_secret_key,
            secure=settings.storage_use_ssl,
        )
        _ensure_bucket(_client)
    return _client


def _ensure_bucket(client: Minio) -> None:
    if not client.bucket_exists(settings.storage_bucket):
        client.make_bucket(settings.storage_bucket)


def upload_file(file_bytes: bytes, object_key: str, content_type: str = "application/octet-stream") -> str:
    client = get_storage_client()
    client.put_object(
        settings.storage_bucket,
        object_key,
        io.BytesIO(file_bytes),
        length=len(file_bytes),
        content_type=content_type,
    )
    return object_key


def download_file(object_key: str) -> bytes:
    client = get_storage_client()
    response = client.get_object(settings.storage_bucket, object_key)
    try:
        return response.read()
    finally:
        response.close()
        response.release_conn()


def get_presigned_url(object_key: str, expires_seconds: int = 3600) -> str:
    from datetime import timedelta
    client = get_storage_client()
    return client.presigned_get_object(
        settings.storage_bucket,
        object_key,
        expires=timedelta(seconds=expires_seconds),
    )


def delete_file(object_key: str) -> None:
    client = get_storage_client()
    try:
        client.remove_object(settings.storage_bucket, object_key)
    except S3Error:
        pass


def build_object_key(project_id: int, category: str, filename: str) -> str:
    return f"projects/{project_id}/{category}/{filename}"
