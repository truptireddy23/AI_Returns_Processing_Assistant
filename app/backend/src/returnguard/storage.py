"""Where return photos live.

- `S3Storage`: Neon Object Storage (or any S3-compatible store) when
  AWS_ENDPOINT_URL_S3 is set. The bucket is private; the API reads objects and
  serves them only to people allowed to see them.
- `LocalStorage`: a folder on disk, for offline work and tests.

Keys are opaque (`returns/<return id>/<uuid>.jpg`); the database stores the key,
never the bytes.
"""

import asyncio
from functools import lru_cache
from pathlib import Path
from typing import TYPE_CHECKING, Protocol

import boto3
from botocore.config import Config
from botocore.exceptions import BotoCoreError, ClientError

from returnguard.config import get_settings

if TYPE_CHECKING:
    from mypy_boto3_s3 import S3Client


class StorageError(Exception):
    """The object store failed or the object is missing."""


class Storage(Protocol):
    name: str

    async def put(self, key: str, data: bytes, content_type: str) -> None: ...
    async def get(self, key: str) -> bytes: ...
    async def delete(self, key: str) -> None: ...


class LocalStorage:
    name = "local"

    def __init__(self, root: Path) -> None:
        self.root = root

    def _path(self, key: str) -> Path:
        path = (self.root / key).resolve()
        if not path.is_relative_to(self.root.resolve()):
            raise StorageError("Invalid storage key")
        return path

    async def put(self, key: str, data: bytes, content_type: str) -> None:
        path = self._path(key)
        await asyncio.to_thread(path.parent.mkdir, parents=True, exist_ok=True)
        await asyncio.to_thread(path.write_bytes, data)

    async def get(self, key: str) -> bytes:
        try:
            return await asyncio.to_thread(self._path(key).read_bytes)
        except FileNotFoundError as exc:
            raise StorageError("Object not found") from exc

    async def delete(self, key: str) -> None:
        await asyncio.to_thread(self._path(key).unlink, missing_ok=True)


class S3Storage:
    name = "s3"

    def __init__(self, client: "S3Client", bucket: str) -> None:
        self.client = client
        self.bucket = bucket

    async def put(self, key: str, data: bytes, content_type: str) -> None:
        try:
            await asyncio.to_thread(
                self.client.put_object,
                Bucket=self.bucket,
                Key=key,
                Body=data,
                ContentType=content_type,
            )
        except (ClientError, BotoCoreError) as exc:
            raise StorageError("Upload to object storage failed") from exc

    async def get(self, key: str) -> bytes:
        try:
            response = await asyncio.to_thread(self.client.get_object, Bucket=self.bucket, Key=key)
            return await asyncio.to_thread(response["Body"].read)
        except (ClientError, BotoCoreError) as exc:
            raise StorageError("Object not found or storage unavailable") from exc

    async def delete(self, key: str) -> None:
        try:
            await asyncio.to_thread(self.client.delete_object, Bucket=self.bucket, Key=key)
        except (ClientError, BotoCoreError) as exc:
            raise StorageError("Delete from object storage failed") from exc


@lru_cache
def get_storage() -> Storage:
    settings = get_settings()
    if settings.aws_endpoint_url_s3:
        client = boto3.client(
            "s3",
            endpoint_url=settings.aws_endpoint_url_s3,
            aws_access_key_id=settings.aws_access_key_id.get_secret_value() or None,
            aws_secret_access_key=settings.aws_secret_access_key.get_secret_value() or None,
            region_name=settings.aws_region,
            # Neon Object Storage requires path-style addressing and SigV4.
            config=Config(
                s3={"addressing_style": "path"},
                signature_version="s3v4",
                retries={"max_attempts": 3, "mode": "standard"},
                connect_timeout=5,
                read_timeout=30,
            ),
        )
        return S3Storage(client, settings.storage_bucket)
    return LocalStorage(Path(settings.local_storage_dir))
