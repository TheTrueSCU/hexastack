"""Unit tests for CircuitBreakerPort and AsyncCircuitBreakerPort abstract contracts."""

from __future__ import annotations

import inspect

import pytest

from hexastack_core.adapters.circuit_breaker import (
    AsyncInMemoryCircuitBreaker,
    InMemoryCircuitBreaker,
)
from hexastack_core.ports.circuit_breaker import (
    AsyncCircuitBreakerPort,
    CircuitBreakerPort,
    CircuitState,
)


def test_circuit_breaker_port_subclass_instantiation() -> None:
    """Verify concrete subclass can be instantiated and executed."""
    breaker: CircuitBreakerPort = InMemoryCircuitBreaker()
    st = breaker.state("svc")
    assert st == CircuitState.CLOSED
    allowed = breaker.allow_execution("svc")
    assert allowed is True
    res = breaker.call("svc", lambda x: x * 2, 5)
    assert res == 10
    breaker.record_success("svc")
    breaker.record_failure("svc", ValueError("err"))
    breaker.reset("svc")


@pytest.mark.anyio
async def test_async_circuit_breaker_port_subclass_instantiation() -> None:
    """Verify concrete async subclass can be instantiated and executed."""
    breaker: AsyncCircuitBreakerPort = AsyncInMemoryCircuitBreaker()
    st = await breaker.state_async("async_svc")
    assert st == CircuitState.CLOSED
    allowed = await breaker.allow_execution_async("async_svc")
    assert allowed is True

    async def dummy_coro(val: str) -> str:
        return f"hello {val}"

    res = await breaker.call_async("async_svc", dummy_coro, "world")
    assert res == "hello world"
    await breaker.record_success_async("async_svc")
    await breaker.record_failure_async("async_svc", ValueError("err"))
    await breaker.reset_async("async_svc")


def test_circuit_state_enum() -> None:
    """Verify CircuitState enum values."""
    assert CircuitState.CLOSED == "closed"
    assert CircuitState.OPEN == "open"
    assert CircuitState.HALF_OPEN == "half_open"


def test_circuit_breaker_port_is_abstract() -> None:
    """Verify that CircuitBreakerPort cannot be instantiated directly and is abstract."""
    is_abs = inspect.isabstract(CircuitBreakerPort)
    assert is_abs is True
    with pytest.raises(TypeError, match="Can't instantiate abstract class"):
        CircuitBreakerPort()  # ty: ignore[call-non-callable] # type: ignore[abstract]


def test_circuit_breaker_port_abstract_methods() -> None:
    """Verify abstract methods on CircuitBreakerPort."""
    expected = {
        "allow_execution",
        "call",
        "record_failure",
        "record_success",
        "reset",
        "state",
    }
    abstracts = CircuitBreakerPort.__abstractmethods__
    diff = expected.difference(abstracts)
    assert len(diff) == 0


def test_async_circuit_breaker_port_is_abstract() -> None:
    """Verify that AsyncCircuitBreakerPort cannot be instantiated directly and is abstract."""
    is_abs = inspect.isabstract(AsyncCircuitBreakerPort)
    assert is_abs is True
    with pytest.raises(TypeError, match="Can't instantiate abstract class"):
        AsyncCircuitBreakerPort()  # ty: ignore[call-non-callable] # type: ignore[abstract]


def test_async_circuit_breaker_port_abstract_methods() -> None:
    """Verify abstract methods on AsyncCircuitBreakerPort."""
    expected = {
        "allow_execution_async",
        "call_async",
        "record_failure_async",
        "record_success_async",
        "reset_async",
        "state_async",
    }
    abstracts = AsyncCircuitBreakerPort.__abstractmethods__
    diff = expected.difference(abstracts)
    assert len(diff) == 0
