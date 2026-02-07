from __future__ import annotations


class DangerousGoodsService:
    def validate_declaration(self, *, un_number: str, packing_group: str) -> tuple[bool, list[str]]:
        issues: list[str] = []
        if not (un_number.startswith("UN") and un_number[2:].isdigit()):
            issues.append("invalid_un_number")
        if packing_group not in {"I", "II", "III"}:
            issues.append("invalid_packing_group")
        return len(issues) == 0, issues


# TODO(owner:dg-compliance): integrate IATA DGR rules database versioning and explanation store.
