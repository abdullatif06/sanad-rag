"""Tiny in-memory sliding-window rate limiter (fine for a single backend instance)."""

import time
from collections import defaultdict, deque
from collections.abc import Callable


class RateLimiter:
    def __init__(self, max_calls: int, per_seconds: float, clock: Callable[[], float] = time.monotonic):
        self.max_calls = max_calls
        self.per_seconds = per_seconds
        self._clock = clock
        self._calls: dict[str, deque[float]] = defaultdict(deque)

    def allow(self, key: str) -> bool:
        now = self._clock()
        calls = self._calls[key]
        while calls and now - calls[0] >= self.per_seconds:
            calls.popleft()
        if len(calls) >= self.max_calls:
            return False
        calls.append(now)
        return True

    def reset(self) -> None:
        self._calls.clear()
