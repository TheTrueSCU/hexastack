import pytest

from hexastack_core.adapters.ratelimit import (
    InMemoryRateLimiter,
    _parse_rate_limit,
)


def test_parse_rate_limit():
    spec1 = _parse_rate_limit("10/minute")
    assert spec1.count == 10
    assert spec1.window_seconds == 60

    spec2 = _parse_rate_limit("5/second")
    assert spec2.count == 5
    assert spec2.window_seconds == 1

    spec3 = _parse_rate_limit("100/hour")
    assert spec3.count == 100
    assert spec3.window_seconds == 3600

    spec4 = _parse_rate_limit("1000/day")
    assert spec4.count == 1000
    assert spec4.window_seconds == 86400

    with pytest.raises(ValueError, match="Invalid rate limit format"):
        _parse_rate_limit("10-minute")

    with pytest.raises(ValueError, match="Invalid rate limit count"):
        _parse_rate_limit("abc/minute")

    with pytest.raises(ValueError, match="Invalid rate limit time unit"):
        _parse_rate_limit("10/decade")


def test_in_memory_rate_limiter_hits_and_resets():
    limiter = InMemoryRateLimiter()

    key = "user:123"
    limit = "3/second"

    assert limiter.hit(key, limit) is True
    assert limiter.hit(key, limit) is True
    assert limiter.hit(key, limit) is True
    # 4th hit exceeds 3/second
    assert limiter.hit(key, limit) is False

    reset_window = limiter.get_reset_window(key, limit)
    assert reset_window >= 1

    # Reset for different key is allowed
    assert limiter.hit("user:456", limit) is True

    # Clear specific key
    limiter.clear(key)
    assert limiter.hit(key, limit) is True

    # Clear all
    limiter.clear()
    assert limiter.get_reset_window(key, limit) == 0
