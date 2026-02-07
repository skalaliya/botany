from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any, Optional, Protocol

import httpx

from libs.common.config import Settings, get_settings
from libs.common.integrations import AdapterHttpConfig, IntegrationError, JsonHttpAdapter
from libs.common.secrets import resolve_secret


class ExportAuthorityAdapter(Protocol):
    provider_name: str

    def submit_export_case(
        self,
        *,
        tenant_id: str,
        export_ref: str,
        payload: Mapping[str, Any],
    ) -> dict[str, Any]: ...


@dataclass
class MockAbfIcsAdapter:
    provider_name: str = "ABF/ICS-mock"

    def submit_export_case(
        self,
        *,
        tenant_id: str,
        export_ref: str,
        payload: Mapping[str, Any],
    ) -> dict[str, Any]:
        return {
            "provider": self.provider_name,
            "tenant_id": tenant_id,
            "export_ref": export_ref,
            "status": "submitted",
            "submission_id": f"abf-{export_ref}",
            "payload": dict(payload),
        }


class HttpAbfIcsAdapter:
    provider_name = "ABF/ICS"

    def __init__(self, *, client: JsonHttpAdapter):
        self._client = client

    def submit_export_case(
        self,
        *,
        tenant_id: str,
        export_ref: str,
        payload: Mapping[str, Any],
    ) -> dict[str, Any]:
        response = self._client.post(
            path="/v1/exports/submit",
            payload={
                "tenant_id": tenant_id,
                "export_ref": export_ref,
                "payload": dict(payload),
            },
            idempotency_key=f"{tenant_id}:abfics:{export_ref}",
        )
        status = str(response.get("status", ""))
        if status not in {"submitted", "accepted", "queued"}:
            raise IntegrationError(f"ABF/ICS returned unsupported status {status!r}")

        return {
            "provider": self.provider_name,
            "tenant_id": tenant_id,
            "export_ref": export_ref,
            "status": status,
            "submission_id": str(response.get("submission_id", "")),
            "payload": dict(payload),
        }


def build_export_authority_adapter(
    settings: Optional[Settings] = None,
    *,
    transport: Optional[httpx.BaseTransport] = None,
) -> ExportAuthorityAdapter:
    runtime_settings = settings or get_settings()
    if runtime_settings.integration_mode != "http":
        return MockAbfIcsAdapter()

    token = resolve_secret("ABF_ICS_API_TOKEN", runtime_settings.abf_ics_token_secret_id)
    client = JsonHttpAdapter(
        config=AdapterHttpConfig(
            provider_name="ABF/ICS",
            base_url=runtime_settings.abf_ics_base_url,
            client_id=runtime_settings.abf_ics_client_id,
            bearer_token=token,
            timeout_seconds=runtime_settings.integration_timeout_seconds,
        ),
        transport=transport,
    )
    return HttpAbfIcsAdapter(client=client)
