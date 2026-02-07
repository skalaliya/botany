from __future__ import annotations

from sqlalchemy.orm import Session

from libs.common.audit import create_audit_event
from libs.common.config import get_settings
from libs.common.integrations import IntegrationError
from modules.awb.adapters import CargoAdapter, build_cargo_adapters


class AwbWorkflowService:
    def __init__(self, adapters: dict[str, CargoAdapter] | None = None):
        self._adapters = adapters or build_cargo_adapters(get_settings())

    def submit_awb(
        self,
        db: Session,
        *,
        tenant_id: str,
        actor_id: str,
        provider_key: str,
        awb_number: str,
        payload: dict[str, object],
    ) -> dict[str, object]:
        adapter = self._adapters.get(provider_key)
        if adapter is None:
            raise ValueError("unknown provider")

        try:
            response = adapter.submit_awb(
                tenant_id=tenant_id,
                awb_number=awb_number,
                payload=payload,
            )
            status = str(response.get("status", "accepted"))
        except IntegrationError as exc:
            response = {"status": "failed", "error": str(exc), "provider": provider_key}
            status = "failed"

        create_audit_event(
            db,
            tenant_id=tenant_id,
            actor_id=actor_id,
            action="awb.submitted_to_provider",
            entity_type="awb_record",
            entity_id=awb_number,
            payload={"provider": provider_key, "status": status, "provider_response": response},
        )
        return response
