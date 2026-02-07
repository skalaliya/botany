from __future__ import annotations

from uuid import uuid4

from sqlalchemy.orm import Session

from libs.common.events import EventBus
from libs.common.models import Document, DocumentClassification
from libs.schemas.events import EventTypes


class ClassificationService:
    def __init__(self, event_bus: EventBus):
        self._event_bus = event_bus

    def classify(self, db: Session, *, document: Document) -> DocumentClassification:
        normalized = document.file_name.lower()
        if "awb" in normalized:
            doc_type, confidence = "awb", 0.94
        elif "invoice" in normalized:
            doc_type, confidence = "fiar_invoice", 0.92
        else:
            doc_type, confidence = "unclassified", 0.55

        classification = DocumentClassification(
            id=f"cls_{uuid4().hex}",
            document_id=document.id,
            tenant_id=document.tenant_id,
            doc_type=doc_type,
            confidence=confidence,
            model_version="clf-v1",
        )
        db.add(classification)
        self._event_bus.publish(
            EventTypes.DOCUMENT_CLASSIFIED,
            {
                "tenant_id": document.tenant_id,
                "document_id": document.id,
                "doc_type": doc_type,
                "confidence": confidence,
            },
        )
        return classification
