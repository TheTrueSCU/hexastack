import inspect

import pytest

from hexastack_core.adapters.ratelimit import InMemoryRateLimiter
from hexastack_core.ports.ratelimit import RateLimiterPort


def test_rate_limiter_port_contract():
    limiter: RateLimiterPort = InMemoryRateLimiter()
    assert limiter.hit("ip:1.2.3.4", "1/minute") is True
    assert limiter.get_reset_window("ip:1.2.3.4", "1/minute") <= 60
    limiter.clear()


def test_rate_limiter_port_is_abstract() -> None:
    """Verify that RateLimiterPort cannot be instantiated directly and is abstract."""
    is_abs = inspect.isabstract(RateLimiterPort)
    assert is_abs is True
    with pytest.raises(TypeError, match="Can't instantiate abstract class"):
        RateLimiterPort()  # ty: ignore[call-non-callable] # type: ignore[abstract]


def test_rate_limiter_port_abstract_methods() -> None:
    """Verify abstract methods on RateLimiterPort."""
    expected = {"clear", "get_reset_window", "hit"}
    abstracts = RateLimiterPort.__abstractmethods__
    diff = expected.difference(abstracts)
    assert len(diff) == 0
