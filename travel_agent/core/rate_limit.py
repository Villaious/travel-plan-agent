from __future__ import annotations

from collections import deque
from contextlib import contextmanager
from threading import BoundedSemaphore, Lock
from time import monotonic, sleep
from typing import Iterator


AMAP_WEB_HARD_LIMIT = 3
AMAP_JS_HARD_LIMIT = 10


class SharedRateLimiter:
    """Limit both concurrent work and request starts in a rolling second."""

    def __init__(self, limit: int) -> None:
        self.limit = max(1, limit)
        self._semaphore = BoundedSemaphore(self.limit)
        self._lock = Lock()
        self._starts: deque[float] = deque()

    @contextmanager
    def acquire(self) -> Iterator[None]:
        self._semaphore.acquire()
        try:
            self._wait_for_start_slot()
            yield
        finally:
            self._semaphore.release()

    def _wait_for_start_slot(self) -> None:
        while True:
            with self._lock:
                now = monotonic()
                while self._starts and now - self._starts[0] >= 1.0:
                    self._starts.popleft()
                if len(self._starts) < self.limit:
                    self._starts.append(now)
                    return
                wait_seconds = max(0.001, 1.0 - (now - self._starts[0]))
            sleep(wait_seconds)


_registry: dict[tuple[str, int], SharedRateLimiter] = {}
_registry_lock = Lock()


def clamp_limit(configured: int, hard_limit: int) -> int:
    return max(1, min(configured, hard_limit))


def get_shared_limiter(bucket: str, configured: int, hard_limit: int) -> SharedRateLimiter:
    effective = clamp_limit(configured, hard_limit)
    key = (bucket, effective)
    with _registry_lock:
        limiter = _registry.get(key)
        if limiter is None:
            limiter = SharedRateLimiter(effective)
            _registry[key] = limiter
    return limiter


def amap_web_limiter(bucket: str, configured: int = AMAP_WEB_HARD_LIMIT) -> SharedRateLimiter:
    return get_shared_limiter(bucket, configured, AMAP_WEB_HARD_LIMIT)