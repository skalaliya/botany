from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


class EventEnvelope(BaseModel):
    event_id: str
    event_type: str
    tenant_id: str
    occurred_at: datetime
    payload: dict[str, object] = Field(default_factory=dict)


class EventTypes:
    DOCUMENT_RECEIVED = "document.received"
    DOCUMENT_PREPROCESSED = "document.preprocessed"
    DOCUMENT_CLASSIFIED = "document.classified"
    DOCUMENT_EXTRACTED = "document.extracted"
    DOCUMENT_VALIDATED = "document.validated"
    REVIEW_REQUIRED = "review.required"
    REVIEW_COMPLETED = "review.completed"
    DISCREPANCY_DETECTED = "discrepancy.detected"
    EXPORT_SUBMISSION_UPDATED = "export.submission.updated"
    INVOICE_DISPUTE_UPDATED = "invoice.dispute.updated"
