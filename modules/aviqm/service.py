from __future__ import annotations

from datetime import datetime, timezone


class AviqmService:
    def decode_vin(self, vin: str) -> dict[str, str]:
        if len(vin) != 17:
            return {"status": "invalid", "reason": "vin_must_be_17_chars"}
        return {"status": "decoded", "wmi": vin[:3], "vds": vin[3:9], "vis": vin[9:]}

    def is_case_expired(self, expiry_iso: str) -> bool:
        expiry = datetime.fromisoformat(expiry_iso)
        return expiry < datetime.now(timezone.utc)


# TODO(owner:vehicle-compliance): implement BMSB rules matrix and quarantine API integration.
