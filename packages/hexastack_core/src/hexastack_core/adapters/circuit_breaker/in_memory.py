"""Thread-safe In-Memory Circuit Breaker Adapters."""

from __future__ import annotations

import threading
import time
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from typing import TypeVar

from hexastack_core.domain.exceptions import CircuitBreakerOpenError
from hexastack_core.ports.circuit_breaker import (
    AsyncCircuitBreakerPort,
    CircuitBreakerPort,
    CircuitState,
)

T = TypeVar("T")


@dataclass
class _CircuitStats:
    """Internal container tracking state, failure counts, and recovery timestamps."""

    state: CircuitState = CircuitState.CLOSED
    failure_count: int = 0
    success_count: int = 0
    last_failure_time: float = 0.0
    half_open_active_calls: int = 0


class InMemoryCircuitBreaker(CircuitBreakerPort):
    """Thread-safe synchronous in-memory circuit breaker adapter.

    Notes/Architectural Intent:
        Implements standard three-state state machine using time.monotonic() and threading.RLock.
        Zero external dependencies, completely isolated in memory.
    """

    def __init__(
        self,
        failure_threshold: int = 5,
        recovery_timeout_seconds: float = 10.0,
        half_open_max_trials: int = 1,
    ) -> None:
        """Initialize in-memory circuit breaker.

        Args:
            failure_threshold: Number of consecutive failures before tripping from CLOSED to OPEN.
            recovery_timeout_seconds: Seconds to remain OPEN before transitioning to HALF_OPEN.
            half_open_max_trials: Maximum number of concurrent probing calls permitted in HALF_OPEN.
        """
        self._failure_threshold = max(1, failure_threshold)
        self._recovery_timeout = max(0.001, recovery_timeout_seconds)
        self._half_open_max_trials = max(1, half_open_max_trials)
        self._breakers: dict[str, _CircuitStats] = {}
        self._lock = threading.RLock()

    def _get_stats(self, name: str) -> _CircuitStats:
        """Get or initialize statistics container for a named breaker."""
        if name not in self._breakers:
            self._breakers[name] = _CircuitStats()
        return self._breakers[name]

    def _evaluate_state(self, stats: _CircuitStats) -> CircuitState:
        """Evaluate state and check for recovery timeout expiration."""
        if stats.state == CircuitState.OPEN:
            now = time.monotonic()
            if now - stats.last_failure_time >= self._recovery_timeout:
                stats.state = CircuitState.HALF_OPEN
                stats.success_count = 0
                stats.half_open_active_calls = 0
        return stats.state

    def state(self, name: str) -> CircuitState:
        """Get current operational state for named breaker."""
        with self._lock:
            stats = self._get_stats(name)
            return self._evaluate_state(stats)

    def allow_execution(self, name: str) -> bool:
        """Check if a call is allowed through the named breaker."""
        with self._lock:
            stats = self._get_stats(name)
            curr_state = self._evaluate_state(stats)

            if curr_state == CircuitState.CLOSED:
                return True
            if curr_state == CircuitState.HALF_OPEN:
                if stats.half_open_active_calls < self._half_open_max_trials:
                    stats.half_open_active_calls += 1
                    return True
                return False
            # OPEN
            return False

    def record_success(self, name: str) -> None:
        """Record successful execution."""
        with self._lock:
            stats = self._get_stats(name)
            curr_state = self._evaluate_state(stats)

            if curr_state == CircuitState.HALF_OPEN:
                stats.state = CircuitState.CLOSED
                stats.failure_count = 0
                stats.success_count = 0
                stats.half_open_active_calls = 0
            elif curr_state == CircuitState.CLOSED:
                stats.failure_count = 0

    def record_failure(self, name: str, exc: Exception | None = None) -> None:
        """Record failed execution."""
        with self._lock:
            stats = self._get_stats(name)
            now = time.monotonic()
            stats.last_failure_time = now
            stats.failure_count += 1

            if stats.state == CircuitState.HALF_OPEN:
                stats.state = CircuitState.OPEN
                stats.half_open_active_calls = 0
            elif stats.state == CircuitState.CLOSED:
                if stats.failure_count >= self._failure_threshold:
                    stats.state = CircuitState.OPEN

    def reset(self, name: str) -> None:
        """Reset named breaker to CLOSED and clear stats."""
        with self._lock:
            if name in self._breakers:
                self._breakers[name] = _CircuitStats()

    def call(
        self, name: str, func: Callable[..., T], *args: object, **kwargs: object
    ) -> T:
        """Execute a callable wrapped with circuit breaker protection."""
        if not self.allow_execution(name):
            msg = f"Circuit breaker '{name}' is OPEN. Call rejected."
            raise CircuitBreakerOpenError(msg)

        try:
            result = func(*args, **kwargs)
            self.record_success(name)
            return result
        except Exception as exc:
            self.record_failure(name, exc)
            raise


class AsyncInMemoryCircuitBreaker(AsyncCircuitBreakerPort):
    """Asynchronous wrapper around InMemoryCircuitBreaker.

    Notes/Architectural Intent:
        Delegates to thread-safe synchronous InMemoryCircuitBreaker without blocking async event loops.
    """

    def __init__(
        self,
        failure_threshold: int = 5,
        recovery_timeout_seconds: float = 10.0,
        half_open_max_trials: int = 1,
        sync_breaker: InMemoryCircuitBreaker | None = None,
    ) -> None:
        """Initialize async in-memory circuit breaker."""
        self._sync = sync_breaker or InMemoryCircuitBreaker(
            failure_threshold=failure_threshold,
            recovery_timeout_seconds=recovery_timeout_seconds,
            half_open_max_trials=half_open_max_trials,
        )

    async def state_async(self, name: str) -> CircuitState:
        """Get operational state asynchronously."""
        return self._sync.state(name)

    async def allow_execution_async(self, name: str) -> bool:
        """Check if call is allowed asynchronously."""
        return self._sync.allow_execution(name)

    async def record_success_async(self, name: str) -> None:
        """Record success asynchronously."""
        self._sync.record_success(name)

    async def record_failure_async(
        self, name: str, exc: Exception | None = None
    ) -> None:
        """Record failure asynchronously."""
        self._sync.record_failure(name, exc)

    async def reset_async(self, name: str) -> None:
        """Reset breaker asynchronously."""
        self._sync.reset(name)

    async def call_async(
        self,
        name: str,
        func: Callable[..., Awaitable[T]],
        *args: object,
        **kwargs: object,
    ) -> T:
        """Execute an async coroutine callable protected by circuit breaker."""
        if not self._sync.allow_execution(name):
            msg = f"Circuit breaker '{name}' is OPEN. Async call rejected."
            raise CircuitBreakerOpenError(msg)

        try:
            result = await func(*args, **kwargs)
            self._sync.record_success(name)
            return result
        except Exception as exc:
            self._sync.record_failure(name, exc)
            raise


__all__ = [
    "AsyncInMemoryCircuitBreaker",
    "InMemoryCircuitBreaker",
]
