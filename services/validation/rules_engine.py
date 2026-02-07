from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Callable

RuleHook = Callable[[dict[str, str]], tuple[bool, str]]


@dataclass(frozen=True)
class RuleResult:
    code: str
    passed: bool
    severity: str
    message: str
    explanation: str
    version: str


@dataclass(frozen=True)
class RulePack:
    id: str
    version: str


class ValidationRulesEngine:
    def __init__(self, pack: RulePack, sanctions_hook: RuleHook | None = None):
        self._pack = pack
        self._sanctions_hook = sanctions_hook or self._default_sanctions_hook
        self._awb_pattern = re.compile(r"^\d{3}-\d{8}$")

    def evaluate(self, *, doc_type: str, fields: dict[str, str]) -> list[RuleResult]:
        results: list[RuleResult] = []
        if doc_type == "awb":
            awb_number = fields.get("awb_number", "")
            passed = bool(self._awb_pattern.match(awb_number))
            results.append(
                RuleResult(
                    code="awb.format",
                    passed=passed,
                    severity="high",
                    message="AWB number must match XXX-XXXXXXXX",
                    explanation=f"validated awb_number={awb_number!r}",
                    version=self._pack.version,
                )
            )

        if "weight_kg" in fields:
            try:
                weight = float(fields["weight_kg"])
                passed = weight > 0
            except ValueError:
                passed = False
            results.append(
                RuleResult(
                    code="shipment.weight",
                    passed=passed,
                    severity="medium",
                    message="Weight must be a positive number",
                    explanation=f"parsed weight_kg={fields.get('weight_kg')!r}",
                    version=self._pack.version,
                )
            )

        hs_code = fields.get("hs_code")
        if hs_code:
            valid_hs = hs_code.isdigit() and len(hs_code) in {6, 8, 10}
            results.append(
                RuleResult(
                    code="compliance.hs_code",
                    passed=valid_hs,
                    severity="high",
                    message="HS code must be numeric with 6, 8, or 10 digits",
                    explanation=f"received hs_code={hs_code!r}",
                    version=self._pack.version,
                )
            )

        sanctions_passed, sanctions_message = self._sanctions_hook(fields)
        results.append(
            RuleResult(
                code="compliance.sanctions",
                passed=sanctions_passed,
                severity="high",
                message="Sanctions screening hook result",
                explanation=sanctions_message,
                version=self._pack.version,
            )
        )

        if not results:
            results.append(
                RuleResult(
                    code="generic.required_fields",
                    passed=False,
                    severity="high",
                    message="No extractable required fields found",
                    explanation="field map is empty",
                    version=self._pack.version,
                )
            )
        return results

    @staticmethod
    def _default_sanctions_hook(fields: dict[str, str]) -> tuple[bool, str]:
        restricted_keywords = ("restricted", "sanctioned")
        haystack = " ".join(fields.values()).lower()
        flagged = any(keyword in haystack for keyword in restricted_keywords)
        if flagged:
            return False, "matched restricted keyword in extracted content"
        return True, "no restricted keyword match"
