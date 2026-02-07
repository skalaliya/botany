from __future__ import annotations

import re
from uuid import uuid4

from sqlalchemy.orm import Session

from libs.common.events import EventBus
from libs.common.models import Document, ExtractedEntity, ValidationResult
from libs.schemas.events import EventTypes

AWB_PATTERN = re.compile(r"^\d{3}-\d{8}$")


class ValidationService:
    def __init__(self, event_bus: EventBus):
        self._event_bus = event_bus

    def validate(
        self,
        db: Session,
        *,
        document: Document,
        doc_type: str,
        entities: list[ExtractedEntity],
    ) -> list[ValidationResult]:
        fields = {entity.field_name: entity.field_value for entity in entities}
        results: list[ValidationResult] = []

        if doc_type == "awb":
            awb_number = fields.get("awb_number", "")
            passed = bool(AWB_PATTERN.match(awb_number))
            results.append(
                ValidationResult(
                    id=f"val_{uuid4().hex}",
                    document_id=document.id,
                    tenant_id=document.tenant_id,
                    rule_code="awb.format",
                    passed=passed,
                    severity="high",
                    message="AWB number must match XXX-XXXXXXXX",
                )
            )

        if "weight_kg" in fields:
            try:
                weight = float(fields["weight_kg"])
                passed = weight > 0
            except ValueError:
                passed = False
            results.append(
                ValidationResult(
                    id=f"val_{uuid4().hex}",
                    document_id=document.id,
                    tenant_id=document.tenant_id,
                    rule_code="shipment.weight",
                    passed=passed,
                    severity="medium",
                    message="Weight must be a positive number",
                )
            )

        if not results:
            results.append(
                ValidationResult(
                    id=f"val_{uuid4().hex}",
                    document_id=document.id,
                    tenant_id=document.tenant_id,
                    rule_code="generic.required_fields",
                    passed=False,
                    severity="high",
                    message="No extractable required fields found",
                )
            )

        for result in results:
            db.add(result)

        self._event_bus.publish(
            EventTypes.DOCUMENT_VALIDATED,
            {
                "tenant_id": document.tenant_id,
                "document_id": document.id,
                "doc_type": doc_type,
                "failed_rules": [result.rule_code for result in results if not result.passed],
            },
        )
        return results
