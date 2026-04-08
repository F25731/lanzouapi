from __future__ import annotations

import threading
import time


class PerSourceRateLimiter:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._next_allowed = {}

    def wait(self, source_key: str, rate_limit_per_minute: int) -> None:
        if rate_limit_per_minute <= 0:
            return

        interval = 60.0 / float(rate_limit_per_minute)
        with self._lock:
            now = time.monotonic()
            next_allowed = self._next_allowed.get(source_key, now)
            sleep_seconds = max(0.0, next_allowed - now)
            self._next_allowed[source_key] = max(now, next_allowed) + interval

        if sleep_seconds > 0:
            time.sleep(sleep_seconds)


source_rate_limiter = PerSourceRateLimiter()
