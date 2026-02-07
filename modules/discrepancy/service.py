from __future__ import annotations


class DiscrepancyService:
    def detect_mismatch(
        self,
        *,
        declared_weight: float,
        actual_weight: float,
        declared_value: float,
        actual_value: float,
    ) -> dict[str, float | bool]:
        weight_delta = abs(declared_weight - actual_weight)
        value_delta = abs(declared_value - actual_value)
        anomaly_score = min(
            1.0,
            (weight_delta / max(actual_weight, 1.0)) * 0.5
            + (value_delta / max(actual_value, 1.0)) * 0.5,
        )
        return {
            "mismatch": anomaly_score > 0.2,
            "anomaly_score": round(anomaly_score, 4),
            "weight_delta": round(weight_delta, 2),
            "value_delta": round(value_delta, 2),
        }
