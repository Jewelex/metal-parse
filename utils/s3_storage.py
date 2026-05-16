# utils/s3_storage.py

"""
MinIO / S3 helper – upload files and bytes to object storage.
Uses boto3 with path-style addressing for MinIO compatibility.
"""

import io
import json
from pathlib import Path
from datetime import datetime

import boto3
from botocore.client import Config


def get_s3_client(
    endpoint_url: str | None = None,
    access_key: str | None = None,
    secret_key: str | None = None,
    region: str = "us-east-1",
):
    """
    Return a boto3 S3 client configured for MinIO.
    Falls back to environment variables / .env values if args are None.
    """
    import os

    endpoint_url = endpoint_url or os.getenv("MINIO_ENDPOINT")
    access_key = access_key or os.getenv("MINIO_ROOT_USER")
    secret_key = secret_key or os.getenv("MINIO_ROOT_PASSWORD")

    return boto3.client(
        "s3",
        endpoint_url=endpoint_url,
        aws_access_key_id=access_key,
        aws_secret_access_key=secret_key,
        region_name=region,
        config=Config(signature_version="s3v4"),
    )


def ensure_bucket(client, bucket: str):
    """Create the bucket if it doesn't already exist."""
    try:
        client.head_bucket(Bucket=bucket)
    except client.exceptions.ClientError:
        client.create_bucket(Bucket=bucket)
        print(f"  🪣  Created bucket: {bucket}")


def upload_bytes(client, bucket: str, key: str, data: bytes, content_type: str = "application/octet-stream"):
    """Upload raw bytes to S3/MinIO."""
    client.put_object(
        Bucket=bucket,
        Key=key,
        Body=data,
        ContentType=content_type,
    )


def upload_json(client, bucket: str, key: str, obj: dict):
    """Serialize a dict to JSON and upload."""
    payload = json.dumps(obj, indent=2, ensure_ascii=False).encode("utf-8")
    upload_bytes(client, bucket, key, payload, content_type="application/json")


def upload_file(client, bucket: str, key: str, file_path: str | Path, content_type: str | None = None):
    """Upload a local file to S3/MinIO."""
    file_path = Path(file_path)

    if content_type is None:
        suffix = file_path.suffix.lower()
        content_type = {
            ".png": "image/png",
            ".jpg": "image/jpeg",
            ".jpeg": "image/jpeg",
            ".html": "text/html",
            ".json": "application/json",
            ".txt": "text/plain",
        }.get(suffix, "application/octet-stream")

    client.upload_file(
        str(file_path),
        bucket,
        key,
        ExtraArgs={"ContentType": content_type},
    )


def build_run_prefix() -> str:
    """
    Return an S3 key prefix like  runs/28-04-2026_10-01-30AM/
    Mirrors the old local folder naming convention.
    """
    label = datetime.now().strftime("%d-%m-%Y_%I-%M-%S%p")
    return f"runs/{label}"


def get_object_url(endpoint_url: str, bucket: str, key: str) -> str:
    """Return the full URL for an object (useful for logging)."""
    return f"{endpoint_url}/{bucket}/{key}"
