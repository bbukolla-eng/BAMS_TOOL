"""
Storage backend — supports MinIO/S3 and local filesystem.
Set STORAGE_BACKEND=local in .env to use local disk (development/desktop mode).
"""
import io
import os
import shutil
from pathlib import Path

from core.config import settings

# ── Local filesystem backend ───────────────────────────────────────────────

_LOCAL_ROOT: Path | None = None


def _local_root() -> Path:
    global _LOCAL_ROOT
    if _LOCAL_ROOT is None:
        path = Path(os.getenv("LOCAL_STORAGE_PATH", settings.local_storage_path))
        path.mkdir(parents=True, exist_ok=True)
        _LOCAL_ROOT = path
    return _LOCAL_ROOT


def _local_path(object_key: str) -> Path:
    p = _local_root() / object_key
    p.parent.mkdir(parents=True, exist_ok=True)
    return p


def _use_local() -> bool:
    return settings.storage_backend.lower() == "local" or os.getenv("STORAGE_BACKEND", "").lower() == "local"


# ── MinIO/S3 backend ───────────────────────────────────────────────────────

_minio_client = None


def _get_minio():
    global _minio_client
    if _minio_client is None:
        from minio import Minio
        _minio_client = Minio(
            settings.storage_endpoint,
            access_key=settings.storage_access_key,
            secret_key=settings.storage_secret_key,
            secure=settings.storage_use_ssl,
        )
        if not _minio_client.bucket_exists(settings.storage_bucket):
            _minio_client.make_bucket(settings.storage_bucket)
    return _minio_client


# ── Public API ─────────────────────────────────────────────────────────────

def upload_file(file_bytes: bytes, object_key: str, content_type: str = "application/octet-stream") -> str:
    if _use_local():
        _local_path(object_key).write_bytes(file_bytes)
        return object_key
    client = _get_minio()
    client.put_object(
        settings.storage_bucket,
        object_key,
        io.BytesIO(file_bytes),
        length=len(file_bytes),
        content_type=content_type,
    )
    return object_key


def download_file(object_key: str) -> bytes:
    if _use_local():
        return _local_path(object_key).read_bytes()
    client = _get_minio()
    response = client.get_object(settings.storage_bucket, object_key)
    try:
        return response.read()
    finally:
        response.close()
        response.release_conn()


def get_presigned_url(object_key: str, expires_seconds: int = 3600) -> str:
    if _use_local():
        # In local mode return a path the API can serve directly
        return f"/api/v1/storage/{object_key}"
    from datetime import timedelta
    client = _get_minio()
    return client.presigned_get_object(
        settings.storage_bucket,
        object_key,
        expires=timedelta(seconds=expires_seconds),
    )


def delete_file(object_key: str) -> None:
    if _use_local():
        p = _local_path(object_key)
        if p.exists():
            p.unlink()
        return
    from minio.error import S3Error
    try:
        _get_minio().remove_object(settings.storage_bucket, object_key)
    except S3Error:
        pass


def build_object_key(project_id: int, category: str, filename: str) -> str:
    return f"projects/{project_id}/{category}/{filename}"
