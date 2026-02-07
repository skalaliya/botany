from __future__ import annotations

from uuid import uuid4

from sqlalchemy.orm import Session

from libs.common.ai import DocumentExtractor, get_document_extractor
from libs.common.config import get_settings
from libs.common.events import EventBus
from libs.common.models import Document, ExtractedEntity
from libs.schemas.events import EventTypes


class ExtractionService:
    def __init__(self, event_bus: EventBus, extractor: DocumentExtractor | None = None):
        self._event_bus = event_bus
        self._extractor = extractor or get_document_extractor(get_settings())

    def extract(
        self,
        db: Session,
        *,
        document: Document,
        doc_type: str,
        text_hint: str,
    ) -> tuple[list[ExtractedEntity], float]:
        fields, confidence_map, model_version = self._extractor.extract(doc_type, text_hint)
        entities: list[ExtractedEntity] = []
        for field_name, field_value in fields.items():
            confidence = confidence_map.get(field_name, 0.5)
            entity = ExtractedEntity(
                id=f"ext_{uuid4().hex}",
                document_id=document.id,
                tenant_id=document.tenant_id,
                field_name=field_name,
                field_value=str(field_value),
                confidence=confidence,
                source_model=model_version,
            )
            db.add(entity)
            entities.append(entity)

        average_confidence = sum(confidence_map.values()) / max(len(confidence_map), 1)
        self._event_bus.publish(
            EventTypes.DOCUMENT_EXTRACTED,
            {
                "tenant_id": document.tenant_id,
                "document_id": document.id,
                "doc_type": doc_type,
                "average_confidence": average_confidence,
            },
        )
        return entities, average_confidence
