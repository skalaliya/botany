from __future__ import annotations

import importlib
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

from libs.common.config import Settings, get_settings


class StorageProvider(Protocol):
    def upload_raw(
        self, tenant_id: str, object_name: str, content: bytes, content_type: str
    ) -> str: ...

    def generate_signed_url(self, uri: str) -> str: ...


@dataclass
class LocalStorageProvider:
    root_path: Path

    def upload_raw(
        self, tenant_id: str, object_name: str, content: bytes, content_type: str
    ) -> str:
        _ = content_type
        destination = self.root_path / tenant_id / object_name
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes(content)
        return f"file://{destination}"

    def generate_signed_url(self, uri: str) -> str:
        return uri


class GCSStorageProvider:
    def __init__(self, settings: Settings):
        if not settings.gcs_raw_bucket:
            raise RuntimeError("gcs_raw_bucket must be configured for GCS backend")
        self._bucket_name = settings.gcs_raw_bucket
        storage_module = importlib.import_module("google.cloud.storage")
        self._client = storage_module.Client(project=settings.gcp_project_id or None)

    def upload_raw(
        self, tenant_id: str, object_name: str, content: bytes, content_type: str
    ) -> str:
        blob_name = f"{tenant_id}/{object_name}"
        bucket = self._client.bucket(self._bucket_name)
        blob = bucket.blob(blob_name)
        blob.upload_from_string(content, content_type=content_type)
        return f"gs://{self._bucket_name}/{blob_name}"

    def generate_signed_url(self, uri: str) -> str:
        if not uri.startswith("gs://"):
            raise ValueError("uri must start with gs://")
        _, remainder = uri.split("gs://", 1)
        bucket_name, object_name = remainder.split("/", 1)
        bucket = self._client.bucket(bucket_name)
        blob = bucket.blob(object_name)
        return str(blob.generate_signed_url(version="v4", expiration=900, method="GET"))


def get_storage_provider(settings: Settings | None = None) -> StorageProvider:
    runtime_settings = settings or get_settings()
    if runtime_settings.storage_backend == "gcs":
        return GCSStorageProvider(runtime_settings)
    return LocalStorageProvider(root_path=Path(runtime_settings.storage_local_root))
