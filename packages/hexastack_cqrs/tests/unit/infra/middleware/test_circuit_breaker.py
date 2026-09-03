"""Unit tests for CircuitBreakerMiddleware, AsyncCircuitBreakerMiddleware, and circuit breaker decorators."""

from __future__ import annotations

import time

import pytest

from hexastack_core.adapters.circuit_breaker.in_memory import (
    AsyncInMemoryCircuitBreaker,
    InMemoryCircuitBreaker,
)
from hexastack_core.adapters.logging import InMemoryLogger
from hexastack_core.domain import Command, Query
from hexastack_core.domain.exceptions import CircuitBreakerOpenError
from hexastack_core.ports.circuit_breaker import CircuitState
from hexastack_cqrs.infra.config import CircuitBreakerMiddlewareConfig
from hexastack_cqrs.infra.decorators import (
    _CIRCUIT_BREAKER_META_ATTR,
    CircuitBreakerMetadata,
    circuit_breaker,
)
from hexastack_cqrs.infra.middleware.circuit_breaker import (
    AsyncCircuitBreakerMiddleware,
    CircuitBreakerMiddleware,
)


class CreateItemCommand(Command):
    item_id: str


class GetItemQuery(Query):
    item_id: str


@circuit_breaker(failure_threshold=3, recovery_timeout_seconds=0.1)
class DecoratedCommand(Command):
    name: str


def test_circuit_breaker_decorator_metadata() -> None:
    """Verify @circuit_breaker attaches metadata to command/query class."""
    meta = getattr(DecoratedCommand, _CIRCUIT_BREAKER_META_ATTR, None)
    assert isinstance(meta, CircuitBreakerMetadata)
    assert meta.failure_threshold == 3
    assert meta.recovery_timeout_seconds == 0.1


def test_sync_circuit_breaker_middleware_pass_through_and_trip() -> None:
    """Verify synchronous CircuitBreakerMiddleware trips open and fast-fails."""
    breaker = InMemoryCircuitBreaker(failure_threshold=2, recovery_timeout_seconds=0.05)
    logger = InMemoryLogger()
    config = CircuitBreakerMiddlewareConfig(enable=True)
    middleware = CircuitBreakerMiddleware(breaker=breaker, config=config, logger=logger)

    cmd = CreateItemCommand(item_id="123")

    # 1. Successful execution
    res = middleware(cmd, lambda c: f"created_{c.item_id}")
    assert res == "created_123"
    assert breaker.state("CreateItemCommand") == CircuitState.CLOSED

    # 2. Failure 1
    with pytest.raises(RuntimeError, match="db down 1"):

        def failing_1(c: CreateItemCommand) -> str:
            raise RuntimeError("db down 1")

        middleware(cmd, failing_1)

    assert breaker.state("CreateItemCommand") == CircuitState.CLOSED

    # 3. Failure 2 -> Trips to OPEN
    with pytest.raises(RuntimeError, match="db down 2"):

        def failing_2(c: CreateItemCommand) -> str:
            raise RuntimeError("db down 2")

        middleware(cmd, failing_2)

    assert breaker.state("CreateItemCommand") == CircuitState.OPEN

    # 4. Fast-fail rejection
    with pytest.raises(CircuitBreakerOpenError, match="Execution rejected"):
        middleware(cmd, lambda c: "never called")

    # 5. Disabled middleware bypasses breaker
    disabled_middleware = CircuitBreakerMiddleware(
        breaker=breaker,
        config=CircuitBreakerMiddlewareConfig(enable=False),
    )
    bypassed = disabled_middleware(cmd, lambda c: "bypassed")
    assert bypassed == "bypassed"


@pytest.mark.anyio
async def test_async_circuit_breaker_middleware_lifecycle() -> None:
    """Verify asynchronous CircuitBreakerMiddleware wraps coroutines and trips open."""
    breaker = AsyncInMemoryCircuitBreaker(
        failure_threshold=2, recovery_timeout_seconds=0.05
    )
    logger = InMemoryLogger()
    config = CircuitBreakerMiddlewareConfig(enable=True)
    middleware = AsyncCircuitBreakerMiddleware(
        breaker=breaker, config=config, logger=logger
    )

    query = GetItemQuery(item_id="456")

    async def async_handler(q: GetItemQuery) -> str:
        return f"item_{q.item_id}"

    async def failing_async_handler(q: GetItemQuery) -> str:
        raise ValueError("async query failure")

    # Success
    res = await middleware(query, async_handler)
    assert res == "item_456"

    # Trip to OPEN
    with pytest.raises(ValueError):
        await middleware(query, failing_async_handler)
    with pytest.raises(ValueError):
        await middleware(query, failing_async_handler)

    assert await breaker.state_async("GetItemQuery") == CircuitState.OPEN

    # Rejection
    with pytest.raises(CircuitBreakerOpenError):
        await middleware(query, async_handler)

    # Recovery
    time.sleep(0.06)
    assert await breaker.state_async("GetItemQuery") == CircuitState.HALF_OPEN

    healed = await middleware(query, async_handler)
    assert healed == "item_456"
    assert await breaker.state_async("GetItemQuery") == CircuitState.CLOSED

    # Disabled async middleware
    disabled = AsyncCircuitBreakerMiddleware(
        breaker=breaker,
        config=CircuitBreakerMiddlewareConfig(enable=False),
    )
    res_disabled = await disabled(query, async_handler)
    assert res_disabled == "item_456"
