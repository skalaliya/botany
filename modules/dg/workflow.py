from __future__ import annotations

from typing import Optional, TypedDict
from uuid import uuid4

from sqlalchemy.orm import Session

from libs.common.audit import create_audit_event
from libs.common.models import ComplianceCheck
from modules.dg.service import DangerousGoodsService, DgRuleEvaluation
from services.review.service import ReviewService


class DgWorkflowResult(TypedDict):
    check_id: str
    valid: bool
    issues: list[str]
    rule_results: list[DgRuleEvaluation]
    review_task_id: Optional[str]


class DangerousGoodsWorkflowService:
    def __init__(self, review_service: ReviewService):
        self._service = DangerousGoodsService()
        self._review = review_service

    def validate_and_record(
        self,
        db: Session,
        *,
        tenant_id: str,
        actor_id: str,
        document_id: str,
        un_number: str,
        packing_group: str,
    ) -> DgWorkflowResult:
        rule_results = self._service.evaluate_declaration(
            un_number=un_number,
            packing_group=packing_group,
        )
        issues = [str(item["rule"]) for item in rule_results if not bool(item["passed"])]
        valid = len(issues) == 0

        check = ComplianceCheck(
            id=f"cmp_{uuid4().hex}",
            tenant_id=tenant_id,
            subject_type="dg_declaration",
            subject_id=document_id,
            check_type="dg.declaration_validation",
            result="pass" if valid else "fail",
            details={"rule_results": rule_results, "issues": issues},
        )
        db.add(check)

        review_task_id: Optional[str] = None
        if not valid:
            task = self._review.queue_low_confidence_review(
                db,
                tenant_id=tenant_id,
                actor_id=actor_id,
                document_id=document_id,
                reason="dg declaration validation failed",
                source="dg_workflow",
                confidence=0.4,
            )
            review_task_id = task.id

        create_audit_event(
            db,
            tenant_id=tenant_id,
            actor_id=actor_id,
            action="dg.declaration.validated",
            entity_type="compliance_check",
            entity_id=check.id,
            payload={"valid": valid, "issues": issues, "review_task_id": review_task_id},
        )

        return {
            "check_id": check.id,
            "valid": valid,
            "issues": issues,
            "rule_results": rule_results,
            "review_task_id": review_task_id,
        }
