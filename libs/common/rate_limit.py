from __future__ import annotations

import time
from collections import defaultdict, deque
from dataclasses import dataclass


@dataclass
class RateLimitConfig:
    max_requests: int = 120
    window_seconds: int = 60


class InMemoryRateLimiter:
    def __init__(self, config: RateLimitConfig | None = None):
        self._config = config or RateLimitConfig()
        self._requests: dict[str, deque[float]] = defaultdict(deque)

    def allow(self, key: str) -> bool:
        now = time.time()
        window_start = now - self._config.window_seconds
        bucket = self._requests[key]
        while bucket and bucket[0] < window_start:
            bucket.popleft()
        if len(bucket) >= self._config.max_requests:
            return False
        bucket.append(now)
        return True
