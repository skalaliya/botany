from __future__ import annotations

import time
from collections import deque
from dataclasses import dataclass


@dataclass
class MetricsSnapshot:
    total_requests: int
    failed_requests: int
    avg_latency_ms: float
    p95_latency_ms: float
    per_route: dict[str, dict[str, int]]


class InMemoryMetrics:
    def __init__(self) -> None:
        self._total_requests = 0
        self._failed_requests = 0
        self._total_latency_ms = 0.0
        self._latency_window: deque[float] = deque(maxlen=5000)
        self._per_route: dict[str, dict[str, int]] = {}

    def record_request(
        self,
        *,
        method: str,
        path: str,
        duration_ms: float,
        status_code: int,
    ) -> None:
        self._total_requests += 1
        self._total_latency_ms += duration_ms
        self._latency_window.append(duration_ms)
        if status_code >= 400:
            self._failed_requests += 1

        route_key = f"{method.upper()} {path}"
        route_metrics = self._per_route.setdefault(
            route_key,
            {"requests": 0, "failed": 0},
        )
        route_metrics["requests"] += 1
        if status_code >= 400:
            route_metrics["failed"] += 1

    def snapshot(self) -> MetricsSnapshot:
        avg_latency = (
            self._total_latency_ms / self._total_requests if self._total_requests else 0.0
        )
        return MetricsSnapshot(
            total_requests=self._total_requests,
            failed_requests=self._failed_requests,
            avg_latency_ms=round(avg_latency, 2),
            p95_latency_ms=round(self._p95_latency(), 2),
            per_route=dict(self._per_route),
        )

    def _p95_latency(self) -> float:
        if not self._latency_window:
            return 0.0
        ordered = sorted(self._latency_window)
        index = int(round((len(ordered) - 1) * 0.95))
        return ordered[index]


class RequestTimer:
    def __init__(self) -> None:
        self._start = time.perf_counter()

    def elapsed_ms(self) -> float:
        return (time.perf_counter() - self._start) * 1000
