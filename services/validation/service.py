from __future__ import annotations

from uuid import uuid4

from sqlalchemy.orm import Session

from libs.common.config import get_settings
from libs.common.events import EventBus
from libs.common.models import Document, ExtractedEntity, ValidationResult
from libs.schemas.events import EventTypes
from services.validation.rules_engine import RulePack, ValidationRulesEngine


class ValidationService:
    def __init__(self, event_bus: EventBus):
        self._event_bus = event_bus
        settings = get_settings()
        self._rules_engine = ValidationRulesEngine(
            default_pack=RulePack(
                id=settings.validation_rule_pack_id,
                version=settings.validation_rule_pack_version,
                description="Configured default validation rule pack",
                regulation="Configured policy",
            ),
        )

    def validate(
        self,
        db: Session,
        *,
        document: Document,
        doc_type: str,
        entities: list[ExtractedEntity],
    ) -> list[ValidationResult]:
        fields = {entity.field_name: entity.field_value for entity in entities}
        rule_results = self._rules_engine.evaluate(doc_type=doc_type, fields=fields)
        results: list[ValidationResult] = []
        for rule in rule_results:
            results.append(
                ValidationResult(
                    id=f"val_{uuid4().hex}",
                    document_id=document.id,
                    tenant_id=document.tenant_id,
                    rule_code=f"{rule.code}@{rule.pack_id}:{rule.version}",
                    passed=rule.passed,
                    severity=rule.severity,
                    message=f"{rule.message} ({rule.explanation})",
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
