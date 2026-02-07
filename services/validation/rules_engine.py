from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Callable, Optional

RuleHook = Callable[[dict[str, str]], tuple[bool, str]]


@dataclass(frozen=True)
class RuleResult:
    code: str
    passed: bool
    severity: str
    message: str
    explanation: str
    version: str
    pack_id: str


@dataclass(frozen=True)
class RulePack:
    id: str
    version: str
    description: str
    regulation: str


DEFAULT_PACKS: dict[tuple[str, str], RulePack] = {
    ("global-default", "2026-02-08"): RulePack(
        id="global-default",
        version="2026-02-08",
        description="Global logistics baseline validations",
        regulation="Global baseline",
    ),
    ("australia-export", "2026-02-08"): RulePack(
        id="australia-export",
        version="2026-02-08",
        description="Australian export controls and declarations",
        regulation="ABF/ICS guidance",
    ),
    ("dg-iata", "2026-02-08"): RulePack(
        id="dg-iata",
        version="2026-02-08",
        description="Dangerous goods checks for IATA declarations",
        regulation="IATA DGR",
    ),
}


class ValidationRulesEngine:
    def __init__(
        self,
        default_pack: RulePack,
        sanctions_hook: Optional[RuleHook] = None,
        packs: Optional[dict[tuple[str, str], RulePack]] = None,
    ):
        self._default_pack = default_pack
        self._sanctions_hook = sanctions_hook or self._default_sanctions_hook
        self._awb_pattern = re.compile(r"^\d{3}-\d{8}$")
        self._pack_registry = dict(packs or DEFAULT_PACKS)

    def evaluate(
        self,
        *,
        doc_type: str,
        fields: dict[str, str],
        pack_id: Optional[str] = None,
        pack_version: Optional[str] = None,
    ) -> list[RuleResult]:
        pack = self._resolve_pack(pack_id=pack_id, pack_version=pack_version)
        results: list[RuleResult] = []

        if doc_type == "awb":
            awb_number = fields.get("awb_number", "")
            passed = bool(self._awb_pattern.match(awb_number))
            results.append(
                self._result(
                    pack=pack,
                    code="awb.format",
                    passed=passed,
                    severity="high",
                    message="AWB number must match XXX-XXXXXXXX",
                    explanation=f"validated awb_number={awb_number!r}",
                )
            )

        if "weight_kg" in fields:
            try:
                weight = float(fields["weight_kg"])
                passed = weight > 0
            except ValueError:
                passed = False
            results.append(
                self._result(
                    pack=pack,
                    code="shipment.weight",
                    passed=passed,
                    severity="medium",
                    message="Weight must be a positive number",
                    explanation=f"parsed weight_kg={fields.get('weight_kg')!r}",
                )
            )

        hs_code = fields.get("hs_code")
        if hs_code:
            valid_hs = hs_code.isdigit() and len(hs_code) in {6, 8, 10}
            results.append(
                self._result(
                    pack=pack,
                    code="compliance.hs_code",
                    passed=valid_hs,
                    severity="high",
                    message="HS code must be numeric with 6, 8, or 10 digits",
                    explanation=f"received hs_code={hs_code!r}",
                )
            )

        if pack.id == "australia-export":
            destination = fields.get("destination_country", "").upper()
            results.append(
                self._result(
                    pack=pack,
                    code="aeca.destination",
                    passed=bool(destination),
                    severity="high",
                    message="Destination country is required for export checks",
                    explanation=f"destination_country={destination!r}",
                )
            )
            if destination == "IR":
                results.append(
                    self._result(
                        pack=pack,
                        code="aeca.restricted_destination",
                        passed=False,
                        severity="high",
                        message="Destination is restricted for export",
                        explanation="destination_country is in restricted set",
                    )
                )

        if pack.id == "dg-iata":
            un_number = fields.get("un_number", "")
            packing_group = fields.get("packing_group", "")
            valid_un = un_number.startswith("UN") and un_number[2:].isdigit()
            valid_group = packing_group in {"I", "II", "III"}
            results.append(
                self._result(
                    pack=pack,
                    code="dg.un_number",
                    passed=valid_un,
                    severity="high",
                    message="UN number must match UN#### format",
                    explanation=f"un_number={un_number!r}",
                )
            )
            results.append(
                self._result(
                    pack=pack,
                    code="dg.packing_group",
                    passed=valid_group,
                    severity="high",
                    message="Packing group must be I, II, or III",
                    explanation=f"packing_group={packing_group!r}",
                )
            )

        sanctions_passed, sanctions_message = self._sanctions_hook(fields)
        results.append(
            self._result(
                pack=pack,
                code="compliance.sanctions",
                passed=sanctions_passed,
                severity="high",
                message="Sanctions screening hook result",
                explanation=sanctions_message,
            )
        )

        if not results:
            results.append(
                self._result(
                    pack=pack,
                    code="generic.required_fields",
                    passed=False,
                    severity="high",
                    message="No extractable required fields found",
                    explanation="field map is empty",
                )
            )
        return results

    def _resolve_pack(self, *, pack_id: Optional[str], pack_version: Optional[str]) -> RulePack:
        if pack_id is None and pack_version is None:
            return self._default_pack

        chosen_id = pack_id or self._default_pack.id
        chosen_version = pack_version or self._default_pack.version
        resolved = self._pack_registry.get((chosen_id, chosen_version))
        if resolved is None:
            return self._default_pack
        return resolved

    @staticmethod
    def _result(
        *,
        pack: RulePack,
        code: str,
        passed: bool,
        severity: str,
        message: str,
        explanation: str,
    ) -> RuleResult:
        return RuleResult(
            code=code,
            passed=passed,
            severity=severity,
            message=message,
            explanation=explanation,
            version=pack.version,
            pack_id=pack.id,
        )

    @staticmethod
    def _default_sanctions_hook(fields: dict[str, str]) -> tuple[bool, str]:
        restricted_keywords = ("restricted", "sanctioned")
        haystack = " ".join(fields.values()).lower()
        flagged = any(keyword in haystack for keyword in restricted_keywords)
        if flagged:
            return False, "matched restricted keyword in extracted content"
        return True, "no restricted keyword match"
