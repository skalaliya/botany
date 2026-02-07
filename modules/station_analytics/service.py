from __future__ import annotations


class StationAnalyticsService:
    def throughput_metrics(self, *, processed: int, delayed: int) -> dict[str, float | int]:
        sla_risk = (delayed / processed) if processed else 0.0
        return {
            "processed": processed,
            "delayed": delayed,
            "sla_risk": round(sla_risk, 4),
        }

    def kpi_summary(
        self,
        *,
        throughput_per_hour: float,
        avg_dwell_minutes: float,
        delayed_shipments: int,
        total_shipments: int,
    ) -> dict[str, float | int | str]:
        bottleneck = "none"
        if avg_dwell_minutes > 90:
            bottleneck = "loading"
        elif throughput_per_hour < 25:
            bottleneck = "staffing"

        sla_risk = (delayed_shipments / total_shipments) if total_shipments else 0.0
        risk_flag = "green"
        if sla_risk >= 0.15:
            risk_flag = "red"
        elif sla_risk >= 0.08:
            risk_flag = "amber"

        return {
            "throughput_per_hour": round(throughput_per_hour, 2),
            "avg_dwell_minutes": round(avg_dwell_minutes, 2),
            "delayed_shipments": delayed_shipments,
            "total_shipments": total_shipments,
            "bottleneck_indicator": bottleneck,
            "sla_risk": round(sla_risk, 4),
            "risk_flag": risk_flag,
        }
