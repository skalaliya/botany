from __future__ import annotations

from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.orm import Session

from libs.common.audit import create_audit_event
from libs.common.events import EventBus
from libs.common.models import Discrepancy, Dispute
from libs.schemas.events import EventTypes
from modules.discrepancy.service import DiscrepancyService


class DiscrepancyWorkflowService:
    def __init__(self, event_bus: EventBus):
        self._service = DiscrepancyService()
        self._event_bus = event_bus

    def create_discrepancy(
        self,
        db: Session,
        *,
        tenant_id: str,
        actor_id: str,
        shipment_id: str,
        declared_weight: float,
        actual_weight: float,
        declared_value: float,
        actual_value: float,
        route_risk_factor: float = 0.0,
        historical_score_bias: float = 0.0,
    ) -> Discrepancy:
        score = self._service.detect_mismatch(
            declared_weight=declared_weight,
            actual_weight=actual_weight,
            declared_value=declared_value,
            actual_value=actual_value,
            route_risk_factor=route_risk_factor,
            historical_score_bias=historical_score_bias,
        )
        discrepancy = Discrepancy(
            id=f"dsp_{uuid4().hex}",
            tenant_id=tenant_id,
            shipment_id=shipment_id,
            discrepancy_type="cross_doc_mismatch",
            score=float(score["anomaly_score"]),
            details={
                "weight_delta": score["weight_delta"],
                "value_delta": score["value_delta"],
                "mismatch": score["mismatch"],
                "risk_level": score["risk_level"],
                "explanations": score["explanations"],
            },
            status="open",
        )
        db.add(discrepancy)
        create_audit_event(
            db,
            tenant_id=tenant_id,
            actor_id=actor_id,
            action="discrepancy.created",
            entity_type="discrepancy",
            entity_id=discrepancy.id,
            payload=discrepancy.details,
        )
        self._event_bus.publish(
            EventTypes.DISCREPANCY_DETECTED,
            {
                "tenant_id": tenant_id,
                "discrepancy_id": discrepancy.id,
                "shipment_id": shipment_id,
                "score": discrepancy.score,
            },
        )
        return discrepancy

    def open_dispute(
        self,
        db: Session,
        *,
        tenant_id: str,
        actor_id: str,
        discrepancy_id: str,
    ) -> Dispute:
        discrepancy_stmt = select(Discrepancy).where(
            Discrepancy.id == discrepancy_id,
            Discrepancy.tenant_id == tenant_id,
        )
        discrepancy = db.execute(discrepancy_stmt).scalar_one_or_none()
        if not discrepancy:
            raise ValueError("discrepancy not found")

        dispute = Dispute(
            id=f"dst_{uuid4().hex}",
            tenant_id=tenant_id,
            discrepancy_id=discrepancy_id,
            status="open",
            opened_by=actor_id,
            resolution_notes=None,
        )
        db.add(dispute)
        discrepancy.status = "in_dispute"
        self._event_bus.publish(
            EventTypes.INVOICE_DISPUTE_UPDATED,
            {
                "tenant_id": tenant_id,
                "dispute_id": dispute.id,
                "discrepancy_id": discrepancy_id,
                "status": dispute.status,
            },
        )
        create_audit_event(
            db,
            tenant_id=tenant_id,
            actor_id=actor_id,
            action="dispute.opened",
            entity_type="dispute",
            entity_id=dispute.id,
            payload={"discrepancy_id": discrepancy_id},
        )
        return dispute
