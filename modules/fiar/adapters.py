from __future__ import annotations

from typing import Protocol


class AccountingExportAdapter(Protocol):
    def export_invoice(self, invoice_id: str, payload: dict[str, object]) -> dict[str, object]: ...


class MockAccountingExportAdapter:
    def export_invoice(self, invoice_id: str, payload: dict[str, object]) -> dict[str, object]:
        return {"invoice_id": invoice_id, "status": "queued", "payload": payload}


# TODO(owner:finance-integrations): implement Xero/NetSuite adapter set with secure credential flow via Secret Manager.
