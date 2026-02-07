from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol


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


# TODO(owner:ml-platform): replace mock extractor with Document AI + Vertex Gemini strict JSON extraction chain.
