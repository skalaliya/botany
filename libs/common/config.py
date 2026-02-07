from __future__ import annotations

from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env.local", env_file_encoding="utf-8", extra="ignore"
    )

    app_name: str = "NexusCargo AI Platform"
    environment: str = "dev"
    database_url: str = "sqlite+pysqlite:///./nexuscargo.db"

    auth_issuer: str = "nexuscargo-local"
    auth_audience: str = "nexuscargo-api"
    auth_jwt_secret: str = Field(default="local-dev-secret-change-me", min_length=16)
    auth_refresh_secret: str = Field(default="local-refresh-secret-change-me", min_length=16)
    access_token_ttl_minutes: int = 30
    refresh_token_ttl_days: int = 7

    tenant_header_name: str = "X-Tenant-Id"
    review_confidence_threshold: float = 0.8

    event_bus_backend: str = "memory"
    gcp_project_id: str = ""
    gcp_pubsub_topic_prefix: str = "nexuscargo"

    storage_backend: str = "local"
    storage_local_root: str = "/tmp/nexuscargo-storage"
    gcs_raw_bucket: str = ""
    gcs_processed_bucket: str = ""

    secret_manager_enabled: bool = False
    secret_manager_project_id: str = ""

    webhook_signing_secret: str = Field(default="local-webhook-signing-secret", min_length=16)
    webhook_max_retries: int = 5

    # TODO(owner:platform-security): Wire Identity Platform JWKS endpoint and key rotation policy.
    identity_platform_jwks_url: str = ""


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
