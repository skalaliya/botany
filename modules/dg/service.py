from __future__ import annotations

from typing import TypedDict


class DgRuleEvaluation(TypedDict):
    rule: str
    passed: bool
    message: str
    explanation: str


class DangerousGoodsService:
    def evaluate_declaration(
        self, *, un_number: str, packing_group: str
    ) -> list[DgRuleEvaluation]:
        results: list[DgRuleEvaluation] = []

        valid_un = un_number.startswith("UN") and un_number[2:].isdigit()
        results.append(
            {
                "rule": "dg.un_number",
                "passed": valid_un,
                "message": "UN number must match UN####",
                "explanation": f"received un_number={un_number!r}",
            }
        )

        valid_group = packing_group in {"I", "II", "III"}
        results.append(
            {
                "rule": "dg.packing_group",
                "passed": valid_group,
                "message": "Packing group must be I, II, or III",
                "explanation": f"received packing_group={packing_group!r}",
            }
        )
        return results

    def validate_declaration(self, *, un_number: str, packing_group: str) -> tuple[bool, list[str]]:
        results = self.evaluate_declaration(un_number=un_number, packing_group=packing_group)
        issues = [str(item["rule"]) for item in results if not bool(item["passed"])]
        return len(issues) == 0, issues


# TODO(owner:dg-compliance): integrate IATA DGR rules database versioning and explanation store.
