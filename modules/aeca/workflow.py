from __future__ import annotations

from uuid import uuid4

from sqlalchemy.orm import Session

from libs.common.audit import create_audit_event
from libs.common.events import EventBus
from libs.common.models import ComplianceCheck, Export
from libs.schemas.events import EventTypes
from modules.aeca.adapters import MockAbfIcsAdapter
from modules.aeca.service import AecaService


class AecaWorkflowService:
    def __init__(self, event_bus: EventBus):
        self._event_bus = event_bus
        self._service = AecaService()
        self._adapter = MockAbfIcsAdapter()

    def create_export_case(
        self,
        db: Session,
        *,
        tenant_id: str,
        actor_id: str,
        export_ref: str,
        destination_country: str,
        hs_code: str,
        required_declarations: list[str],
    ) -> Export:
        valid, issues = self._service.validate_export(
            hs_code=hs_code,
            destination_country=destination_country,
        )
        missing_declarations = [decl for decl in required_declarations if not decl.strip()]
        issue_list = issues + (["missing_required_declarations"] if missing_declarations else [])
        status = "ready_for_submission" if valid and not missing_declarations else "review_required"

        export_case = Export(
            id=f"exp_{uuid4().hex}",
            tenant_id=tenant_id,
            export_ref=export_ref,
            destination_country=destination_country,
            status=status,
        )
        db.add(export_case)
        db.add(
            ComplianceCheck(
                id=f"cmp_{uuid4().hex}",
                tenant_id=tenant_id,
                subject_type="export",
                subject_id=export_case.id,
                check_type="aeca.initial_validation",
                result="pass" if not issue_list else "fail",
                details={"issues": issue_list, "hs_code": hs_code},
            )
        )
        create_audit_event(
            db,
            tenant_id=tenant_id,
            actor_id=actor_id,
            action="aeca.export.created",
            entity_type="export",
            entity_id=export_case.id,
            payload={
                "export_ref": export_ref,
                "destination_country": destination_country,
                "status": status,
            },
        )
        return export_case

    def submit_export_case(
        self,
        db: Session,
        *,
        tenant_id: str,
        actor_id: str,
        export_case: Export,
        payload: dict[str, object],
    ) -> dict[str, object]:
        response = self._adapter.submit_export_case(export_case.export_ref, payload)
        export_case.status = "submitted"
        self._event_bus.publish(
            EventTypes.EXPORT_SUBMISSION_UPDATED,
            {
                "tenant_id": tenant_id,
                "export_id": export_case.id,
                "export_ref": export_case.export_ref,
                "provider_status": response.get("status", "unknown"),
            },
        )
        create_audit_event(
            db,
            tenant_id=tenant_id,
            actor_id=actor_id,
            action="aeca.export.submitted",
            entity_type="export",
            entity_id=export_case.id,
            payload={"provider_response": response},
        )
        return response
