"""Unit tests for CircuitBreakerPort and AsyncCircuitBreakerPort abstract contracts."""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import TypeVar

import pytest

from hexastack_core.ports.circuit_breaker import (
    AsyncCircuitBreakerPort,
    CircuitBreakerPort,
    CircuitState,
)

T = TypeVar("T")


class DummySyncBreaker(CircuitBreakerPort):
    """Concrete dummy implementation for testing abstract method compliance."""

    def state(self, name: str) -> CircuitState:
        return CircuitState.CLOSED

    def allow_execution(self, name: str) -> bool:
        return True

    def record_success(self, name: str) -> None:
        pass

    def record_failure(self, name: str, exc: Exception | None = None) -> None:
        pass

    def reset(self, name: str) -> None:
        pass

    def call(
        self, name: str, func: Callable[..., T], *args: object, **kwargs: object
    ) -> T:
        return func(*args, **kwargs)


class DummyAsyncBreaker(AsyncCircuitBreakerPort):
    """Concrete dummy async implementation for testing async method compliance."""

    async def state_async(self, name: str) -> CircuitState:
        return CircuitState.CLOSED

    async def allow_execution_async(self, name: str) -> bool:
        return True

    async def record_success_async(self, name: str) -> None:
        pass

    async def record_failure_async(
        self, name: str, exc: Exception | None = None
    ) -> None:
        pass

    async def reset_async(self, name: str) -> None:
        pass

    async def call_async(
        self,
        name: str,
        func: Callable[..., Awaitable[T]],
        *args: object,
        **kwargs: object,
    ) -> T:
        return await func(*args, **kwargs)


def test_circuit_breaker_port_subclass_instantiation() -> None:
    """Verify concrete subclass can be instantiated and executed."""
    breaker = DummySyncBreaker()
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
    breaker = DummyAsyncBreaker()
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
