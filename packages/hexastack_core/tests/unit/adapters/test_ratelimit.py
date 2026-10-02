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

    # Test unit aliases and plurals
    assert _parse_rate_limit("2/sec").window_seconds == 1
    assert _parse_rate_limit("2/s").window_seconds == 1
    assert _parse_rate_limit("2/seconds").window_seconds == 1
    assert _parse_rate_limit("2/min").window_seconds == 60
    assert _parse_rate_limit("2/m").window_seconds == 60
    assert _parse_rate_limit("2/minutes").window_seconds == 60
    assert _parse_rate_limit("2/hr").window_seconds == 3600
    assert _parse_rate_limit("2/h").window_seconds == 3600
    assert _parse_rate_limit("2/hours").window_seconds == 3600
    assert _parse_rate_limit("2/d").window_seconds == 86400
    assert _parse_rate_limit("2/days").window_seconds == 86400

    with pytest.raises(
        ValueError,
        match="Invalid rate limit format '10-minute'. Expected format '<count>/<unit>' \\(e.g. '10/minute'\\).",
    ):
        _parse_rate_limit("10-minute")

    with pytest.raises(
        ValueError, match="Invalid rate limit count 'abc' in 'abc/minute'."
    ):
        _parse_rate_limit("abc/minute")

    with pytest.raises(
        ValueError,
        match="Invalid rate limit time unit 'decade' in '10/decade'. Supported units: second, minute, hour, day.",
    ):
        _parse_rate_limit("10/decade")


def test_in_memory_rate_limiter_hits_and_resets(monkeypatch: pytest.MonkeyPatch):
    import time

    limiter = InMemoryRateLimiter()

    key = "user:123"
    limit = "3/second"

    assert limiter.get_reset_window(key, limit) == 0

    current_time = 1000.0
    monkeypatch.setattr(time, "time", lambda: current_time)

    res1 = limiter.hit(key, limit)
    assert res1 is True
    res2 = limiter.hit(key, limit)
    assert res2 is True
    res3 = limiter.hit(key, limit)
    assert res3 is True
    # 4th hit exceeds 3/second
    res4 = limiter.hit(key, limit)
    assert res4 is False

    reset_window = limiter.get_reset_window(key, limit)
    assert reset_window == 1

    # Advance time past sliding window (1.1s later)
    current_time = 1001.1
    # Old hits are evicted, hit allowed
    res5 = limiter.hit(key, limit)
    assert res5 is True
    assert len(limiter._hits[key]) == 1

    # Reset for different key is allowed
    res_other = limiter.hit("user:456", limit)
    assert res_other is True

    # Clear specific key
    limiter.clear(key)
    assert key not in limiter._hits
    res_cleared = limiter.hit(key, limit)
    assert res_cleared is True

    # Clear all
    limiter.clear()
    assert len(limiter._hits) == 0
    assert limiter.get_reset_window(key, limit) == 0
