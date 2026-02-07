from __future__ import annotations

import importlib
import json
from dataclasses import dataclass, field
from typing import Protocol

from libs.common.config import Settings, get_settings


class DocumentExtractor(Protocol):
    def extract(
        self, doc_type: str, text_hint: str
    ) -> tuple[dict[str, str], dict[str, float], str]: ...


@dataclass
class MockDocumentExtractor:
    model_version: str = "mock-gemini-1"

    def extract(
        self, doc_type: str, text_hint: str
    ) -> tuple[dict[str, str], dict[str, float], str]:
        normalized_hint = text_hint.lower()
        if doc_type == "awb":
            fields = {
                "awb_number": "123-12345678" if "lowconf" not in normalized_hint else "123-INVALID",
                "shipper": "Demo Shipper Pty Ltd",
                "consignee": "Demo Consignee Pty Ltd",
                "weight_kg": "1200.50",
            }
            confidence = {
                "awb_number": 0.55 if "lowconf" in normalized_hint else 0.95,
                "shipper": 0.94,
                "consignee": 0.93,
                "weight_kg": 0.92,
            }
            return fields, confidence, self.model_version

        fields = {
            "invoice_number": "INV-001",
            "amount": "1000.00",
            "currency": "AUD",
        }
        confidence = {
            "invoice_number": 0.90,
            "amount": 0.91,
            "currency": 0.90,
        }
        return fields, confidence, self.model_version


@dataclass
class GCPDocumentAIExtractor:
    settings: Settings
    fallback: MockDocumentExtractor = field(default_factory=MockDocumentExtractor)

    def extract(
        self, doc_type: str, text_hint: str
    ) -> tuple[dict[str, str], dict[str, float], str]:
        try:
            parsed_text = self._ocr_with_document_ai(text_hint)
            fields, confidence = self._extract_with_vertex(parsed_text, doc_type)
            model_version = f"documentai+{self.settings.vertex_model_name}"
            return fields, confidence, model_version
        except Exception:
            fields, confidence, model = self.fallback.extract(doc_type, text_hint)
            return fields, confidence, f"{model}-fallback"

    def _ocr_with_document_ai(self, text_hint: str) -> str:
        documentai_module = importlib.import_module("google.cloud.documentai")
        client = documentai_module.DocumentProcessorServiceClient()
        processor_path = client.processor_path(
            self.settings.gcp_project_id,
            self.settings.gcp_location,
            self.settings.documentai_processor_id,
        )
        raw_document = documentai_module.RawDocument(
            content=text_hint.encode("utf-8"),
            mime_type="text/plain",
        )
        request = documentai_module.ProcessRequest(name=processor_path, raw_document=raw_document)
        response = client.process_document(request=request)
        if response.document and response.document.text:
            return str(response.document.text)
        return text_hint

    def _extract_with_vertex(
        self, parsed_text: str, doc_type: str
    ) -> tuple[dict[str, str], dict[str, float]]:
        vertexai_module = importlib.import_module("vertexai")
        generative_models = importlib.import_module("vertexai.generative_models")

        vertexai_module.init(
            project=self.settings.gcp_project_id,
            location=self.settings.gcp_location,
        )
        model = generative_models.GenerativeModel(self.settings.vertex_model_name)

        prompt = (
            "Return strict JSON with this exact shape: "
            "{\"fields\":{\"key\":\"value\"},\"confidence\":{\"key\":0.0}}. "
            f"Document type: {doc_type}. "
            f"Source text: {parsed_text[:4000]}"
        )
        response = model.generate_content(prompt)
        raw_text = str(response.text).strip()
        payload = json.loads(raw_text)

        fields = {str(key): str(value) for key, value in payload.get("fields", {}).items()}
        confidence = {
            str(key): float(value) for key, value in payload.get("confidence", {}).items()
        }
        if not fields:
            raise ValueError("vertex response missing fields")
        return fields, confidence


def get_document_extractor(settings: Settings | None = None) -> DocumentExtractor:
    runtime_settings = settings or get_settings()
    if runtime_settings.ai_backend == "gcp":
        return GCPDocumentAIExtractor(runtime_settings)
    return MockDocumentExtractor()
