"""Unit tests for InMemoryCircuitBreaker and AsyncInMemoryCircuitBreaker."""

from __future__ import annotations

import time

import pytest

from hexastack_core.adapters.circuit_breaker.in_memory import (
    AsyncInMemoryCircuitBreaker,
    InMemoryCircuitBreaker,
)
from hexastack_core.domain.exceptions import CircuitBreakerOpenError
from hexastack_core.ports.circuit_breaker import CircuitState


def test_in_memory_circuit_breaker_sync_state_machine() -> None:
    """Verify state transitions: CLOSED -> OPEN -> HALF_OPEN -> CLOSED."""
    breaker = InMemoryCircuitBreaker(
        failure_threshold=3,
        recovery_timeout_seconds=0.05,
        half_open_max_trials=1,
    )

    # 1. Initially CLOSED
    assert breaker.state("db") == CircuitState.CLOSED
    assert breaker.allow_execution("db") is True

    # Successful call
    res = breaker.call("db", lambda x: x + 1, 10)
    assert res == 11

    # 2. Failures below threshold
    with pytest.raises(ValueError, match="fail 1"):

        def failing_1():
            raise ValueError("fail 1")

        breaker.call("db", failing_1)

    assert breaker.state("db") == CircuitState.CLOSED
    assert breaker.allow_execution("db") is True

    # 3. Trip to OPEN on 3 consecutive failures
    with pytest.raises(ValueError):

        def failing_2():
            raise ValueError("fail 2")

        breaker.call("db", failing_2)

    with pytest.raises(ValueError):

        def failing_3():
            raise ValueError("fail 3")

        breaker.call("db", failing_3)

    assert breaker.state("db") == CircuitState.OPEN
    assert breaker.allow_execution("db") is False

    # 4. Fail-fast rejection while OPEN
    with pytest.raises(CircuitBreakerOpenError, match="is OPEN. Call rejected"):
        breaker.call("db", lambda: "never reached")

    # 5. Wait for recovery timeout -> HALF_OPEN
    time.sleep(0.06)
    assert breaker.state("db") == CircuitState.HALF_OPEN

    # 6. Successful trial heals circuit -> CLOSED
    res_trial = breaker.call("db", lambda: "success probe")
    assert res_trial == "success probe"
    assert breaker.state("db") == CircuitState.CLOSED
    assert breaker.allow_execution("db") is True

    # 7. Trip to HALF_OPEN and then fail -> back to OPEN
    breaker.record_failure("db", ValueError("err1"))
    breaker.record_failure("db", ValueError("err2"))
    breaker.record_failure("db", ValueError("err3"))
    assert breaker.state("db") == CircuitState.OPEN

    time.sleep(0.06)
    assert breaker.state("db") == CircuitState.HALF_OPEN

    with pytest.raises(RuntimeError, match="trial failed"):

        def failing_trial():
            raise RuntimeError("trial failed")

        breaker.call("db", failing_trial)

    assert breaker.state("db") == CircuitState.OPEN

    # 8. Reset
    breaker.reset("db")
    assert breaker.state("db") == CircuitState.CLOSED


@pytest.mark.anyio
async def test_async_in_memory_circuit_breaker_state_machine() -> None:
    """Verify async in-memory circuit breaker operations."""
    breaker = AsyncInMemoryCircuitBreaker(
        failure_threshold=2,
        recovery_timeout_seconds=0.05,
    )

    assert await breaker.state_async("api") == CircuitState.CLOSED
    assert await breaker.allow_execution_async("api") is True

    async def async_success() -> str:
        return "async ok"

    async def async_fail() -> str:
        raise ValueError("async fail")

    res = await breaker.call_async("api", async_success)
    assert res == "async ok"

    # Trip to OPEN
    with pytest.raises(ValueError):
        await breaker.call_async("api", async_fail)
    with pytest.raises(ValueError):
        await breaker.call_async("api", async_fail)

    assert await breaker.state_async("api") == CircuitState.OPEN

    # Rejection
    with pytest.raises(CircuitBreakerOpenError):
        await breaker.call_async("api", async_success)

    # Recovery
    time.sleep(0.06)
    assert await breaker.state_async("api") == CircuitState.HALF_OPEN

    # Probe recovery
    probe_res = await breaker.call_async("api", async_success)
    assert probe_res == "async ok"
    assert await breaker.state_async("api") == CircuitState.CLOSED

    await breaker.reset_async("api")
    assert await breaker.state_async("api") == CircuitState.CLOSED
