from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any, Optional, Protocol

import httpx

from libs.common.config import Settings, get_settings
from libs.common.integrations import AdapterHttpConfig, IntegrationError, JsonHttpAdapter
from libs.common.secrets import resolve_secret


class CargoAdapter(Protocol):
    provider_name: str

    def submit_awb(
        self,
        *,
        tenant_id: str,
        awb_number: str,
        payload: Mapping[str, Any],
    ) -> dict[str, Any]: ...


@dataclass
class MockCargoAdapter:
    provider_name: str

    def submit_awb(
        self,
        *,
        tenant_id: str,
        awb_number: str,
        payload: Mapping[str, Any],
    ) -> dict[str, Any]:
        return {
            "provider": self.provider_name,
            "tenant_id": tenant_id,
            "awb_number": awb_number,
            "status": "accepted",
            "external_id": f"{self.provider_name.lower()}-{awb_number}",
            "payload": dict(payload),
        }


class HttpCargoAdapter:
    def __init__(self, *, provider_name: str, client: JsonHttpAdapter):
        self.provider_name = provider_name
        self._client = client

    def submit_awb(
        self,
        *,
        tenant_id: str,
        awb_number: str,
        payload: Mapping[str, Any],
    ) -> dict[str, Any]:
        response = self._client.post(
            path="/v1/shipments/awb",
            payload={
                "tenant_id": tenant_id,
                "awb_number": awb_number,
                "payload": dict(payload),
            },
            idempotency_key=f"{tenant_id}:{self.provider_name}:{awb_number}",
        )
        status = str(response.get("status", ""))
        if status not in {"accepted", "queued", "received"}:
            raise IntegrationError(
                f"{self.provider_name} returned unsupported status {status!r}"
            )

        return {
            "provider": self.provider_name,
            "tenant_id": tenant_id,
            "awb_number": awb_number,
            "status": status,
            "external_id": str(response.get("external_id", "")),
            "payload": dict(payload),
        }


def _http_adapter(
    *,
    provider_name: str,
    base_url: str,
    client_id: str,
    token_env: str,
    token_secret_id: str,
    timeout_seconds: int,
    transport: Optional[httpx.BaseTransport],
) -> HttpCargoAdapter:
    token = resolve_secret(token_env, token_secret_id)
    client = JsonHttpAdapter(
        config=AdapterHttpConfig(
            provider_name=provider_name,
            base_url=base_url,
            client_id=client_id,
            bearer_token=token,
            timeout_seconds=timeout_seconds,
        ),
        transport=transport,
    )
    return HttpCargoAdapter(provider_name=provider_name, client=client)


def build_cargo_adapters(
    settings: Optional[Settings] = None,
    *,
    transport: Optional[httpx.BaseTransport] = None,
) -> dict[str, CargoAdapter]:
    runtime_settings = settings or get_settings()
    if runtime_settings.integration_mode != "http":
        return {
            "champ": MockCargoAdapter(provider_name="CHAMP"),
            "ibs_icargo": MockCargoAdapter(provider_name="IBS iCargo"),
            "cargowise": MockCargoAdapter(provider_name="CargoWise"),
        }

    return {
        "champ": _http_adapter(
            provider_name="CHAMP",
            base_url=runtime_settings.champ_base_url,
            client_id=runtime_settings.champ_client_id,
            token_env="CHAMP_API_TOKEN",
            token_secret_id=runtime_settings.champ_token_secret_id,
            timeout_seconds=runtime_settings.integration_timeout_seconds,
            transport=transport,
        ),
        "ibs_icargo": _http_adapter(
            provider_name="IBS iCargo",
            base_url=runtime_settings.ibs_base_url,
            client_id=runtime_settings.ibs_client_id,
            token_env="IBS_API_TOKEN",
            token_secret_id=runtime_settings.ibs_token_secret_id,
            timeout_seconds=runtime_settings.integration_timeout_seconds,
            transport=transport,
        ),
        "cargowise": _http_adapter(
            provider_name="CargoWise",
            base_url=runtime_settings.cargowise_base_url,
            client_id=runtime_settings.cargowise_client_id,
            token_env="CARGOWISE_API_TOKEN",
            token_secret_id=runtime_settings.cargowise_token_secret_id,
            timeout_seconds=runtime_settings.integration_timeout_seconds,
            transport=transport,
        ),
    }
