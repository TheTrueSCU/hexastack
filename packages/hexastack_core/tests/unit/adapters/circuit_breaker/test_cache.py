"""Unit tests for CacheCircuitBreaker and AsyncCacheCircuitBreaker."""

from __future__ import annotations

import time

import pytest

from hexastack_core.adapters.cache.in_memory import (
    AsyncInMemoryCache,
    InMemoryCache,
)
from hexastack_core.adapters.circuit_breaker.cache import (
    AsyncCacheCircuitBreaker,
    CacheCircuitBreaker,
)
from hexastack_core.domain.exceptions import CircuitBreakerOpenError
from hexastack_core.ports.circuit_breaker import CircuitState


def test_cache_circuit_breaker_sync_lifecycle() -> None:
    """Verify cache-backed circuit breaker state transitions."""
    cache = InMemoryCache()
    breaker = CacheCircuitBreaker(
        cache=cache,
        failure_threshold=2,
        recovery_timeout_seconds=0.05,
    )

    assert breaker.state("http_client") == CircuitState.CLOSED
    assert breaker.allow_execution("http_client") is True

    # 1. Success call
    res = breaker.call("http_client", lambda: "ok")
    assert res == "ok"

    # 2. Trip to OPEN
    with pytest.raises(RuntimeError):

        def failing():
            raise RuntimeError("err")

        breaker.call("http_client", failing)

    assert breaker.state("http_client") == CircuitState.CLOSED

    with pytest.raises(RuntimeError):

        def failing_again():
            raise RuntimeError("err2")

        breaker.call("http_client", failing_again)

    assert breaker.state("http_client") == CircuitState.OPEN
    assert breaker.allow_execution("http_client") is False

    # 3. Call rejected
    with pytest.raises(CircuitBreakerOpenError):
        breaker.call("http_client", lambda: "never")

    # 4. Recovery
    time.sleep(0.06)
    assert breaker.state("http_client") == CircuitState.HALF_OPEN

    # 5. Success resets to CLOSED
    res2 = breaker.call("http_client", lambda: "recovered")
    assert res2 == "recovered"
    assert breaker.state("http_client") == CircuitState.CLOSED

    # 6. Reset
    breaker.reset("http_client")
    assert breaker.state("http_client") == CircuitState.CLOSED


@pytest.mark.anyio
async def test_async_cache_circuit_breaker_lifecycle() -> None:
    """Verify async cache-backed circuit breaker state transitions."""
    cache = AsyncInMemoryCache()
    breaker = AsyncCacheCircuitBreaker(
        cache=cache,
        failure_threshold=2,
        recovery_timeout_seconds=0.05,
    )

    assert await breaker.state_async("async_http") == CircuitState.CLOSED
    assert await breaker.allow_execution_async("async_http") is True

    async def async_ok() -> str:
        return "async success"

    async def async_err() -> str:
        raise ValueError("failed async")

    res = await breaker.call_async("async_http", async_ok)
    assert res == "async success"

    # Trip to OPEN
    with pytest.raises(ValueError):
        await breaker.call_async("async_http", async_err)
    with pytest.raises(ValueError):
        await breaker.call_async("async_http", async_err)

    assert await breaker.state_async("async_http") == CircuitState.OPEN

    # Rejection
    with pytest.raises(CircuitBreakerOpenError):
        await breaker.call_async("async_http", async_ok)

    # Recovery
    time.sleep(0.06)
    assert await breaker.state_async("async_http") == CircuitState.HALF_OPEN

    # Success heals
    heal_res = await breaker.call_async("async_http", async_ok)
    assert heal_res == "async success"
    assert await breaker.state_async("async_http") == CircuitState.CLOSED

    # Trip and fail in HALF_OPEN
    await breaker.record_failure_async("async_http", ValueError("1"))
    await breaker.record_failure_async("async_http", ValueError("2"))
    assert await breaker.state_async("async_http") == CircuitState.OPEN

    time.sleep(0.06)
    assert await breaker.state_async("async_http") == CircuitState.HALF_OPEN

    with pytest.raises(ValueError):
        await breaker.call_async("async_http", async_err)
    assert await breaker.state_async("async_http") == CircuitState.OPEN

    await breaker.reset_async("async_http")
    assert await breaker.state_async("async_http") == CircuitState.CLOSED
