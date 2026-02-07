from __future__ import annotations


class AecaService:
    def validate_export(self, *, hs_code: str, destination_country: str) -> tuple[bool, list[str]]:
        issues: list[str] = []
        if len(hs_code) not in {6, 8, 10} or not hs_code.isdigit():
            issues.append("invalid_hs_code")
        if len(destination_country) not in {2, 3}:
            issues.append("invalid_destination_country")
        return len(issues) == 0, issues


# TODO(owner:trade-compliance): add ABF/ICS submission workflow with mocked-to-real adapter swap.
