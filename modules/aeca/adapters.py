from __future__ import annotations

from typing import Protocol


class ExportAuthorityAdapter(Protocol):
    def submit_export_case(
        self, export_ref: str, payload: dict[str, object]
    ) -> dict[str, object]: ...


class MockAbfIcsAdapter:
    def submit_export_case(self, export_ref: str, payload: dict[str, object]) -> dict[str, object]:
        return {
            "provider": "ABF/ICS-mock",
            "export_ref": export_ref,
            "status": "submitted",
            "payload": payload,
        }


# TODO(owner:trade-compliance): implement ABF/ICS production API adapter once credentials and API spec are approved.
