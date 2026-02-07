from __future__ import annotations

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from libs.common.models import Discrepancy, Document, ReviewTask


class AnalyticsService:
    def overview(self, db: Session, *, tenant_id: str) -> dict[str, float | int]:
        total_documents = db.scalar(
            select(func.count()).select_from(Document).where(Document.tenant_id == tenant_id)
        )
        open_review = db.scalar(
            select(func.count())
            .select_from(ReviewTask)
            .where(ReviewTask.tenant_id == tenant_id, ReviewTask.status == "open")
        )
        total_discrepancies = db.scalar(
            select(func.count()).select_from(Discrepancy).where(Discrepancy.tenant_id == tenant_id)
        )

        total_documents_int = int(total_documents or 0)
        review_int = int(open_review or 0)
        discrepancy_int = int(total_discrepancies or 0)
        rate = (discrepancy_int / total_documents_int) if total_documents_int else 0.0

        return {
            "total_documents": total_documents_int,
            "open_review_tasks": review_int,
            "discrepancy_rate": round(rate, 4),
        }


# TODO(owner:data-platform): add BigQuery batch export job and scheduled transforms for station analytics.
