from __future__ import annotations

from typing import Protocol


class CargoAdapter(Protocol):
    def submit_awb(self, awb_number: str, payload: dict[str, object]) -> dict[str, object]: ...


class MockChampAdapter:
    def submit_awb(self, awb_number: str, payload: dict[str, object]) -> dict[str, object]:
        return {
            "provider": "CHAMP",
            "awb_number": awb_number,
            "status": "accepted",
            "payload": payload,
        }


class MockIbsICargoAdapter:
    def submit_awb(self, awb_number: str, payload: dict[str, object]) -> dict[str, object]:
        return {
            "provider": "IBS iCargo",
            "awb_number": awb_number,
            "status": "accepted",
            "payload": payload,
        }


class MockCargoWiseAdapter:
    def submit_awb(self, awb_number: str, payload: dict[str, object]) -> dict[str, object]:
        return {
            "provider": "CargoWise",
            "awb_number": awb_number,
            "status": "accepted",
            "payload": payload,
        }


# TODO(owner:integration-team): implement OAuth/OIDC secured provider clients for CHAMP, IBS iCargo, and CargoWise.
