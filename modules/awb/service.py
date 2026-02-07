from __future__ import annotations

import re

AWB_REGEX = re.compile(r"^\d{3}-\d{8}$")


class AwbService:
    def validate_awb(self, *, awb_number: str, weight_kg: float) -> tuple[bool, list[str]]:
        messages: list[str] = []
        if not AWB_REGEX.match(awb_number):
            messages.append("AWB format must be XXX-XXXXXXXX")
        if weight_kg <= 0:
            messages.append("Weight must be positive")
        return len(messages) == 0, messages

    def historical_party_autocomplete(self, *, partial_name: str) -> list[str]:
        # TODO(owner:awb-module): back this with tenant-scoped party history index in PostgreSQL.
        if not partial_name:
            return []
        mock_parties = ["Acme Logistics", "Aero Freight", "Alpha Imports"]
        return [party for party in mock_parties if partial_name.lower() in party.lower()]
