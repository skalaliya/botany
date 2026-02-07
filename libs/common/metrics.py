from __future__ import annotations

import time
from dataclasses import dataclass


@dataclass
class MetricsSnapshot:
    total_requests: int
    failed_requests: int
    avg_latency_ms: float


class InMemoryMetrics:
    def __init__(self) -> None:
        self._total_requests = 0
        self._failed_requests = 0
        self._total_latency_ms = 0.0

    def record_request(self, *, duration_ms: float, status_code: int) -> None:
        self._total_requests += 1
        self._total_latency_ms += duration_ms
        if status_code >= 400:
            self._failed_requests += 1

    def snapshot(self) -> MetricsSnapshot:
        avg_latency = (
            self._total_latency_ms / self._total_requests if self._total_requests else 0.0
        )
        return MetricsSnapshot(
            total_requests=self._total_requests,
            failed_requests=self._failed_requests,
            avg_latency_ms=round(avg_latency, 2),
        )


class RequestTimer:
    def __init__(self) -> None:
        self._start = time.perf_counter()

    def elapsed_ms(self) -> float:
        return (time.perf_counter() - self._start) * 1000
