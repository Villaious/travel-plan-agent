from concurrent.futures import ThreadPoolExecutor
from threading import Lock
from time import monotonic, sleep

from travel_agent.core.rate_limit import SharedRateLimiter, clamp_limit


def test_amap_rate_limiter_clamps_and_throttles():
    assert clamp_limit(99, 3) == 3
    assert clamp_limit(0, 3) == 1

    limiter = SharedRateLimiter(3)
    lock = Lock()
    active = 0
    max_active = 0

    def call_service():
        nonlocal active, max_active
        with limiter.acquire():
            with lock:
                active += 1
                max_active = max(max_active, active)
            sleep(0.03)
            with lock:
                active -= 1

    started = monotonic()
    with ThreadPoolExecutor(max_workers=6) as executor:
        list(executor.map(lambda _: call_service(), range(6)))

    assert max_active <= 3
    assert monotonic() - started >= 0.9