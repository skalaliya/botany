from __future__ import annotations

import os
from typing import Final

from libs.common.config import get_settings

DEV_PLACEHOLDER_PREFIX: Final[str] = "dev-placeholder-"


def _fetch_from_secret_manager(secret_id: str) -> str:
    settings = get_settings()
    if not settings.secret_manager_project_id:
        raise RuntimeError("secret_manager_project_id is required when secret_manager_enabled=true")

    from google.cloud import secretmanager  # Imported lazily to keep local tests lightweight.

    client = secretmanager.SecretManagerServiceClient()
    secret_path = (
        f"projects/{settings.secret_manager_project_id}/secrets/{secret_id}/versions/latest"
    )
    response = client.access_secret_version(request={"name": secret_path})
    return response.payload.data.decode("utf-8")


def resolve_secret(env_name: str, secret_manager_id: str) -> str:
    env_value = os.getenv(env_name)
    if env_value:
        return env_value

    settings = get_settings()
    if settings.secret_manager_enabled:
        return _fetch_from_secret_manager(secret_manager_id)

    if settings.environment.lower() in {"staging", "prod", "production"}:
        raise RuntimeError(
            f"secret {secret_manager_id} must be sourced from Secret Manager in non-dev environments"
        )

    return f"{DEV_PLACEHOLDER_PREFIX}{secret_manager_id}"
