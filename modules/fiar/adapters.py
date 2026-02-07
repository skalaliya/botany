from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any, Optional, Protocol

import httpx

from libs.common.config import Settings, get_settings
from libs.common.integrations import AdapterHttpConfig, IntegrationError, JsonHttpAdapter
from libs.common.secrets import resolve_secret


class AccountingExportAdapter(Protocol):
    provider_name: str

    def export_invoice(
        self,
        *,
        tenant_id: str,
        invoice_id: str,
        payload: Mapping[str, Any],
    ) -> dict[str, Any]: ...


@dataclass
class MockAccountingExportAdapter:
    provider_name: str = "AccountingMock"

    def export_invoice(
        self,
        *,
        tenant_id: str,
        invoice_id: str,
        payload: Mapping[str, Any],
    ) -> dict[str, Any]:
        return {
            "provider": self.provider_name,
            "tenant_id": tenant_id,
            "invoice_id": invoice_id,
            "status": "queued",
            "external_id": f"acct-{invoice_id}",
            "payload": dict(payload),
        }


class HttpAccountingExportAdapter:
    def __init__(self, *, provider_name: str, client: JsonHttpAdapter):
        self.provider_name = provider_name
        self._client = client

    def export_invoice(
        self,
        *,
        tenant_id: str,
        invoice_id: str,
        payload: Mapping[str, Any],
    ) -> dict[str, Any]:
        response = self._client.post(
            path="/v1/invoices/export",
            payload={
                "tenant_id": tenant_id,
                "invoice_id": invoice_id,
                "payload": dict(payload),
            },
            idempotency_key=f"{tenant_id}:{self.provider_name}:{invoice_id}",
        )
        status = str(response.get("status", ""))
        if status not in {"queued", "exported", "accepted"}:
            raise IntegrationError(
                f"{self.provider_name} returned unsupported status {status!r}"
            )
        return {
            "provider": self.provider_name,
            "tenant_id": tenant_id,
            "invoice_id": invoice_id,
            "status": status,
            "external_id": str(response.get("external_id", "")),
            "payload": dict(payload),
        }


def build_accounting_export_adapter(
    settings: Optional[Settings] = None,
    *,
    transport: Optional[httpx.BaseTransport] = None,
) -> AccountingExportAdapter:
    runtime_settings = settings or get_settings()
    if runtime_settings.integration_mode != "http":
        return MockAccountingExportAdapter()

    token = resolve_secret("ACCOUNTING_EXPORT_API_TOKEN", runtime_settings.accounting_export_token_secret_id)
    client = JsonHttpAdapter(
        config=AdapterHttpConfig(
            provider_name="Accounting",
            base_url=runtime_settings.accounting_export_base_url,
            client_id=runtime_settings.accounting_export_client_id,
            bearer_token=token,
            timeout_seconds=runtime_settings.integration_timeout_seconds,
        ),
        transport=transport,
    )
    return HttpAccountingExportAdapter(provider_name="Accounting", client=client)
