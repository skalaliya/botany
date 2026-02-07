from __future__ import annotations

from libs.common.events import EventBus
from libs.common.models import Document
from libs.schemas.events import EventTypes


class PreprocessingService:
    def __init__(self, event_bus: EventBus):
        self._event_bus = event_bus

    def preprocess(self, *, document: Document) -> str:
        # Hook for deskew/denoise/contrast operations.
        # TODO(owner:doc-intel): integrate image preprocessing pipeline in Cloud Run job.
        artifact_uri = f"{document.storage_uri}#preprocessed"
        self._event_bus.publish(
            EventTypes.DOCUMENT_PREPROCESSED,
            {
                "tenant_id": document.tenant_id,
                "document_id": document.id,
                "artifact_uri": artifact_uri,
            },
        )
        return artifact_uri
