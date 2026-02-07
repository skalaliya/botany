from __future__ import annotations


class FiarService:
    def three_way_match(
        self,
        *,
        invoice_amount: float,
        contract_amount: float,
        delivered_amount: float,
        tolerance_percent: float,
    ) -> tuple[bool, list[str]]:
        discrepancies: list[str] = []
        tolerance_ratio = tolerance_percent / 100

        if not self._within_tolerance(invoice_amount, contract_amount, tolerance_ratio):
            discrepancies.append("invoice_vs_contract")
        if not self._within_tolerance(invoice_amount, delivered_amount, tolerance_ratio):
            discrepancies.append("invoice_vs_delivery")

        return len(discrepancies) == 0, discrepancies

    @staticmethod
    def _within_tolerance(left: float, right: float, tolerance_ratio: float) -> bool:
        if right == 0:
            return left == 0
        delta = abs(left - right) / right
        return delta <= tolerance_ratio

    def compute_savings(self, *, billed_amount: float, expected_amount: float) -> float:
        return round(max(0.0, billed_amount - expected_amount), 2)
