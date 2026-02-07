from __future__ import annotations

from typing import TypedDict


class DiscrepancyScore(TypedDict):
    mismatch: bool
    anomaly_score: float
    weight_delta: float
    value_delta: float
    risk_level: str
    explanations: list[str]


class DiscrepancyService:
    def detect_mismatch(
        self,
        *,
        declared_weight: float,
        actual_weight: float,
        declared_value: float,
        actual_value: float,
        route_risk_factor: float = 0.0,
        historical_score_bias: float = 0.0,
    ) -> DiscrepancyScore:
        weight_delta = abs(declared_weight - actual_weight)
        value_delta = abs(declared_value - actual_value)
        weight_component = (weight_delta / max(actual_weight, 1.0)) * 0.45
        value_component = (value_delta / max(actual_value, 1.0)) * 0.45
        route_component = min(max(route_risk_factor, 0.0), 1.0) * 0.05
        historical_component = min(max(historical_score_bias, 0.0), 1.0) * 0.05

        anomaly_score = min(1.0, weight_component + value_component + route_component + historical_component)
        risk_level = "low"
        if anomaly_score >= 0.7:
            risk_level = "high"
        elif anomaly_score >= 0.35:
            risk_level = "medium"

        explanations = [
            f"weight_delta={weight_delta:.2f}",
            f"value_delta={value_delta:.2f}",
            f"route_risk_factor={route_risk_factor:.2f}",
            f"historical_score_bias={historical_score_bias:.2f}",
        ]
        return {
            "mismatch": anomaly_score > 0.2,
            "anomaly_score": round(anomaly_score, 4),
            "weight_delta": round(weight_delta, 2),
            "value_delta": round(value_delta, 2),
            "risk_level": risk_level,
            "explanations": explanations,
        }
