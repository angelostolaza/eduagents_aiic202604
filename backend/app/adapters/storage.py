"""Object storage adapter — MinIO (dev) / S3 or Cloudflare R2 (prod) via boto3."""
from __future__ import annotations

import hashlib
from functools import lru_cache

import boto3
from botocore.config import Config
from botocore.exceptions import ClientError

from app.config import get_settings


class StorageAdapter:
    def __init__(self) -> None:
        settings = get_settings()
        self._bucket = settings.storage_bucket
        self._client = boto3.client(
            "s3",
            endpoint_url=settings.storage_endpoint or None,
            aws_access_key_id=settings.storage_access_key,
            aws_secret_access_key=settings.storage_secret_key,
            region_name=settings.storage_region,
            config=Config(connect_timeout=5, retries={"max_attempts": 1}),
        )
        self._public_url_base = getattr(settings, "storage_public_url", "")

    async def upload(self, key: str, data: bytes, content_type: str) -> str:
        """Upload bytes to the bucket and return the public URL."""
        import asyncio

        loop = asyncio.get_event_loop()
        await loop.run_in_executor(
            None,
            lambda: self._client.put_object(
                Bucket=self._bucket,
                Key=key,
                Body=data,
                ContentType=content_type,
            ),
        )
        if self._public_url_base:
            return f"{self._public_url_base.rstrip('/')}/{key}"
        settings = get_settings()
        endpoint = settings.storage_endpoint or "http://localhost:9000"
        return f"{endpoint}/{self._bucket}/{key}"

    def presign_url(self, key: str, expiry_seconds: int = 3600) -> str:
        return self._client.generate_presigned_url(
            "get_object",
            Params={"Bucket": self._bucket, "Key": key},
            ExpiresIn=expiry_seconds,
        )

    @staticmethod
    def content_hash(data: bytes) -> str:
        return hashlib.sha256(data).hexdigest()

    async def ensure_bucket(self) -> None:
        """Create the bucket if it doesn't exist (used on startup)."""
        import asyncio

        loop = asyncio.get_event_loop()
        try:
            await loop.run_in_executor(
                None,
                lambda: self._client.head_bucket(Bucket=self._bucket),
            )
        except ClientError:
            await loop.run_in_executor(
                None,
                lambda: self._client.create_bucket(Bucket=self._bucket),
            )
