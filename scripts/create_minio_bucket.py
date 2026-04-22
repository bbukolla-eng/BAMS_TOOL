"""
Create required MinIO buckets.
Run once after MinIO is started.
Usage: python scripts/create_minio_bucket.py
"""
import sys
sys.path.insert(0, "backend")

from minio import Minio
from minio.error import S3Error
from core.config import settings

BUCKETS = ["bams-drawings", "bams-specs", "bams-exports", "bams-ml-models"]


def main():
    client = Minio(
        settings.storage_endpoint,
        access_key=settings.storage_access_key,
        secret_key=settings.storage_secret_key,
        secure=settings.storage_use_ssl,
    )
    for bucket in BUCKETS:
        try:
            if not client.bucket_exists(bucket):
                client.make_bucket(bucket)
                print(f"Created bucket: {bucket}")
            else:
                print(f"Bucket already exists: {bucket}")
        except S3Error as e:
            print(f"Error creating {bucket}: {e}")


if __name__ == "__main__":
    main()
