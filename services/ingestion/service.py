from __future__ import annotations

import hashlib
from uuid import uuid4

from sqlalchemy.orm import Session

from libs.common.audit import create_audit_event
from libs.common.config import get_settings
from libs.common.events import EventBus
from libs.common.models import Document, DocumentVersion
from libs.common.storage import StorageProvider
from libs.schemas.events import EventTypes
from services.classification.service import ClassificationService
from services.extraction.service import ExtractionService
from services.preprocessing.service import PreprocessingService
from services.review.service import ReviewService
from services.validation.service import ValidationService

ALLOWED_CONTENT_TYPES = {
    "application/pdf",
    "image/png",
    "image/jpeg",
    "text/plain",
}


class IngestionService:
    def __init__(
        self,
        event_bus: EventBus,
        storage_provider: StorageProvider,
        preprocessing_service: PreprocessingService,
        classification_service: ClassificationService,
        extraction_service: ExtractionService,
        validation_service: ValidationService,
        review_service: ReviewService,
    ):
        self._event_bus = event_bus
        self._storage = storage_provider
        self._preprocessing = preprocessing_service
        self._classification = classification_service
        self._extraction = extraction_service
        self._validation = validation_service
        self._review = review_service

    def ingest_and_process(
        self,
        db: Session,
        *,
        tenant_id: str,
        actor_id: str,
        file_name: str,
        content_type: str,
        payload_bytes: bytes,
        text_hint: str,
    ) -> dict[str, object]:
        if content_type not in ALLOWED_CONTENT_TYPES:
            raise ValueError("unsupported content type")

        self._run_virus_scan_hook(payload_bytes)

        digest = hashlib.sha256(payload_bytes).hexdigest()
        object_name = f"raw/{uuid4().hex}-{file_name}"
        storage_uri = self._storage.upload_raw(
            tenant_id=tenant_id,
            object_name=object_name,
            content=payload_bytes,
            content_type=content_type,
        )

        document = Document(
            id=f"doc_{uuid4().hex}",
            tenant_id=tenant_id,
            file_name=file_name,
            content_type=content_type,
            status="received",
            storage_uri=storage_uri,
            created_by=actor_id,
        )
        db.add(document)

        version = DocumentVersion(
            id=f"dv_{uuid4().hex}",
            document_id=document.id,
            tenant_id=tenant_id,
            version_number=1,
            storage_uri=storage_uri,
            checksum=digest,
        )
        db.add(version)

        create_audit_event(
            db,
            tenant_id=tenant_id,
            actor_id=actor_id,
            action="document.ingested",
            entity_type="document",
            entity_id=document.id,
            payload={"file_name": file_name, "content_type": content_type},
        )

        self._event_bus.publish(
            EventTypes.DOCUMENT_RECEIVED,
            {"tenant_id": tenant_id, "document_id": document.id, "content_type": content_type},
        )

        _artifact_uri = self._preprocessing.preprocess(document=document)
        classification = self._classification.classify(db, document=document)
        entities, average_confidence = self._extraction.extract(
            db,
            document=document,
            doc_type=classification.doc_type,
            text_hint=text_hint,
        )
        validation_results = self._validation.validate(
            db,
            document=document,
            doc_type=classification.doc_type,
            entities=entities,
        )

        settings = get_settings()
        review_required = classification.confidence < settings.review_confidence_threshold
        review_required = (
            review_required or average_confidence < settings.review_confidence_threshold
        )
        review_required = review_required or any(not result.passed for result in validation_results)

        if review_required:
            self._review.queue_low_confidence_review(
                db,
                tenant_id=tenant_id,
                actor_id=actor_id,
                document_id=document.id,
                reason="low-confidence or validation-failure",
                source="pipeline",
                confidence=min(classification.confidence, average_confidence),
            )
            document.status = "review_required"
        else:
            document.status = "validated"

        return {
            "document_id": document.id,
            "status": document.status,
            "review_required": review_required,
            "doc_type": classification.doc_type,
        }

    def _run_virus_scan_hook(self, payload_bytes: bytes) -> None:
        # TODO(owner:platform-security): invoke ClamAV sidecar or malware scanner service in Cloud Run.
        _ = payload_bytes
