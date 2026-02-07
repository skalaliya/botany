from __future__ import annotations

from datetime import datetime, timezone
from uuid import uuid4

from sqlalchemy import and_, select
from sqlalchemy.orm import Session

from libs.common.audit import create_audit_event
from libs.common.events import EventBus
from libs.common.models import Correction, ReviewTask
from libs.schemas.events import EventTypes


class ReviewService:
    def __init__(self, event_bus: EventBus):
        self._event_bus = event_bus

    def queue_low_confidence_review(
        self,
        db: Session,
        *,
        tenant_id: str,
        actor_id: str,
        document_id: str,
        reason: str,
        source: str,
        confidence: float,
    ) -> ReviewTask:
        existing_stmt = select(ReviewTask).where(
            and_(
                ReviewTask.tenant_id == tenant_id,
                ReviewTask.document_id == document_id,
                ReviewTask.status == "open",
            )
        )
        existing = db.execute(existing_stmt).scalar_one_or_none()
        if existing:
            return existing

        task = ReviewTask(
            id=f"rvw_{uuid4().hex}",
            tenant_id=tenant_id,
            document_id=document_id,
            reason=reason,
            source=source,
            status="open",
            confidence=confidence,
        )
        db.add(task)

        create_audit_event(
            db,
            tenant_id=tenant_id,
            actor_id=actor_id,
            action="review.task.created",
            entity_type="review_task",
            entity_id=task.id,
            payload={"document_id": document_id, "reason": reason, "source": source},
        )
        self._event_bus.publish(
            EventTypes.REVIEW_REQUIRED,
            {
                "tenant_id": tenant_id,
                "document_id": document_id,
                "review_task_id": task.id,
                "reason": reason,
                "source": source,
                "confidence": confidence,
            },
        )
        return task

    def complete_review(
        self,
        db: Session,
        *,
        tenant_id: str,
        actor_id: str,
        review_task_id: str,
        approved: bool,
        corrections: list[dict[str, str]],
    ) -> ReviewTask:
        stmt = select(ReviewTask).where(
            ReviewTask.id == review_task_id,
            ReviewTask.tenant_id == tenant_id,
        )
        task = db.execute(stmt).scalar_one_or_none()
        if not task:
            raise ValueError("review task not found")

        task.status = "approved" if approved else "rejected"
        task.completed_at = datetime.now(timezone.utc)
        for correction in corrections:
            db.add(
                Correction(
                    id=f"cor_{uuid4().hex}",
                    tenant_id=tenant_id,
                    review_task_id=task.id,
                    field_name=correction["field_name"],
                    old_value=correction["old_value"],
                    new_value=correction["new_value"],
                    reason_tag=correction["reason_tag"],
                    corrected_by=actor_id,
                )
            )

        create_audit_event(
            db,
            tenant_id=tenant_id,
            actor_id=actor_id,
            action="review.task.completed",
            entity_type="review_task",
            entity_id=task.id,
            payload={"approved": approved, "correction_count": len(corrections)},
        )
        self._event_bus.publish(
            EventTypes.REVIEW_COMPLETED,
            {
                "tenant_id": tenant_id,
                "review_task_id": review_task_id,
                "approved": approved,
                "correction_count": len(corrections),
            },
        )
        return task
