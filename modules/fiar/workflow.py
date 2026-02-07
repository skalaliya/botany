from __future__ import annotations

from sqlalchemy.orm import Session

from libs.common.audit import create_audit_event
from libs.common.config import get_settings
from libs.common.integrations import IntegrationError
from modules.fiar.adapters import AccountingExportAdapter, build_accounting_export_adapter


class FiarWorkflowService:
    def __init__(self, adapter: AccountingExportAdapter | None = None):
        self._adapter = adapter or build_accounting_export_adapter(get_settings())

    def export_invoice(
        self,
        db: Session,
        *,
        tenant_id: str,
        actor_id: str,
        invoice_id: str,
        payload: dict[str, object],
    ) -> dict[str, object]:
        try:
            response = self._adapter.export_invoice(
                tenant_id=tenant_id,
                invoice_id=invoice_id,
                payload=payload,
            )
            status = str(response.get("status", "queued"))
        except IntegrationError as exc:
            response = {"status": "failed", "error": str(exc)}
            status = "failed"

        create_audit_event(
            db,
            tenant_id=tenant_id,
            actor_id=actor_id,
            action="fiar.invoice.exported",
            entity_type="freight_invoice",
            entity_id=invoice_id,
            payload={"status": status, "provider_response": response},
        )
        return response
