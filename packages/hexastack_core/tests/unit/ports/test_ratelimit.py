from hexastack_core.adapters.ratelimit import InMemoryRateLimiter
from hexastack_core.ports.ratelimit import RateLimiterPort


def test_rate_limiter_port_contract():
    limiter: RateLimiterPort = InMemoryRateLimiter()
    assert limiter.hit("ip:1.2.3.4", "1/minute") is True
    assert limiter.get_reset_window("ip:1.2.3.4", "1/minute") <= 60
    limiter.clear()
