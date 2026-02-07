from __future__ import annotations


class StationAnalyticsService:
    def throughput_metrics(self, *, processed: int, delayed: int) -> dict[str, float | int]:
        sla_risk = (delayed / processed) if processed else 0.0
        return {
            "processed": processed,
            "delayed": delayed,
            "sla_risk": round(sla_risk, 4),
        }
