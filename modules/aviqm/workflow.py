from __future__ import annotations

from datetime import date, datetime, timedelta, timezone
from uuid import uuid4

from sqlalchemy.orm import Session

from libs.common.audit import create_audit_event
from libs.common.models import Alert, ComplianceCheck, VehicleImportCase
from modules.aviqm.service import AviqmService


class AviqmWorkflowService:
    def __init__(self) -> None:
        self._service = AviqmService()

    def create_case(
        self,
        db: Session,
        *,
        tenant_id: str,
        actor_id: str,
        case_ref: str,
        vin: str,
        expiry_date: date | None,
        bmsb_risk_month: int | None,
    ) -> VehicleImportCase:
        decoded = self._service.decode_vin(vin)
        status = "ready" if decoded.get("status") == "decoded" else "review_required"

        case = VehicleImportCase(
            id=f"vic_{uuid4().hex}",
            tenant_id=tenant_id,
            case_ref=case_ref,
            vin=vin,
            status=status,
            expiry_date=expiry_date,
        )
        db.add(case)

        bmsb_risk = bool(bmsb_risk_month and bmsb_risk_month in {9, 10, 11, 12, 1, 2, 3, 4})
        db.add(
            ComplianceCheck(
                id=f"cmp_{uuid4().hex}",
                tenant_id=tenant_id,
                subject_type="vehicle_import_case",
                subject_id=case.id,
                check_type="aviqm.bmsb_risk_window",
                result="warn" if bmsb_risk else "pass",
                details={"bmsb_risk_month": bmsb_risk_month, "vin_decode": decoded},
            )
        )

        if expiry_date and expiry_date < (datetime.now(timezone.utc).date() + timedelta(days=30)):
            db.add(
                Alert(
                    id=f"alt_{uuid4().hex}",
                    tenant_id=tenant_id,
                    alert_type="aviqm.expiry_soon",
                    severity="high",
                    message=f"Vehicle import case {case_ref} expires on {expiry_date.isoformat()}",
                )
            )

        create_audit_event(
            db,
            tenant_id=tenant_id,
            actor_id=actor_id,
            action="aviqm.case.created",
            entity_type="vehicle_import_case",
            entity_id=case.id,
            payload={"case_ref": case_ref, "status": status, "bmsb_risk": bmsb_risk},
        )
        return case
