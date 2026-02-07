from __future__ import annotations

import json
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any, Optional

import httpx


class IntegrationError(RuntimeError):
    pass


@dataclass
class AdapterHttpConfig:
    provider_name: str
    base_url: str
    client_id: str
    bearer_token: str
    timeout_seconds: int = 20


class JsonHttpAdapter:
    def __init__(
        self,
        *,
        config: AdapterHttpConfig,
        transport: Optional[httpx.BaseTransport] = None,
    ):
        self._config = config
        self._client = httpx.Client(
            base_url=config.base_url.rstrip("/"),
            timeout=config.timeout_seconds,
            transport=transport,
        )

    def post(
        self,
        *,
        path: str,
        payload: Mapping[str, Any],
        idempotency_key: str,
    ) -> dict[str, Any]:
        headers = {
            "Authorization": f"Bearer {self._config.bearer_token}",
            "X-Client-Id": self._config.client_id,
            "X-Idempotency-Key": idempotency_key,
            "Content-Type": "application/json",
        }
        response = self._client.post(path, headers=headers, json=payload)
        if response.status_code >= 400:
            raise IntegrationError(
                f"{self._config.provider_name} HTTP error {response.status_code}: {response.text}"
            )

        try:
            data = response.json()
        except json.JSONDecodeError as exc:
            raise IntegrationError(
                f"{self._config.provider_name} returned non-JSON response"
            ) from exc

        if not isinstance(data, dict):
            raise IntegrationError(f"{self._config.provider_name} returned invalid JSON payload")
        return data

    def close(self) -> None:
        self._client.close()
