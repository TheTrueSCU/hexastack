"""Distributed Circuit Breaker Adapters backed by CachePort / AsyncCachePort."""

from __future__ import annotations

import time
from collections.abc import Awaitable, Callable
from typing import TypeVar

from hexastack_core.domain.exceptions import CircuitBreakerOpenError
from hexastack_core.ports.cache import AsyncCachePort, CachePort
from hexastack_core.ports.circuit_breaker import (
    AsyncCircuitBreakerPort,
    CircuitBreakerPort,
    CircuitState,
)

T = TypeVar("T")


class CacheCircuitBreaker(CircuitBreakerPort):
    """Distributed synchronous circuit breaker adapter backed by CachePort (Redis/Valkey/Memory).

    Notes/Architectural Intent:
        Stores breaker state, failure counts, and timestamps in a shared CachePort key.
        Enables multi-pod Kubernetes microservices to share circuit trip state across cluster nodes.
    """

    def __init__(
        self,
        cache: CachePort,
        failure_threshold: int = 5,
        recovery_timeout_seconds: float = 10.0,
        key_prefix: str = "hexastack:circuit_breaker:",
    ) -> None:
        """Initialize cache-backed circuit breaker.

        Args:
            cache: CachePort instance for distributed state synchronization.
            failure_threshold: Number of consecutive failures to trip open.
            recovery_timeout_seconds: Duration in seconds breaker remains open.
            key_prefix: String prefix prepended to cache keys.
        """
        self._cache = cache
        self._failure_threshold = max(1, failure_threshold)
        self._recovery_timeout = max(0.001, recovery_timeout_seconds)
        self._prefix = key_prefix

    def _key(self, name: str) -> str:
        return f"{self._prefix}{name}"

    def _get_data(self, name: str) -> dict[str, object]:
        raw = self._cache.get(self._key(name))
        if isinstance(raw, dict):
            return dict(raw)
        return {
            "state": CircuitState.CLOSED.value,
            "failure_count": 0,
            "last_failure_time": 0.0,
        }

    def _save_data(self, name: str, data: dict[str, object]) -> None:
        ttl = self._recovery_timeout * 3
        self._cache.set(self._key(name), data, ttl_seconds=ttl)

    def state(self, name: str) -> CircuitState:
        """Get current operational state."""
        data = self._get_data(name)
        curr_state = CircuitState(str(data.get("state", CircuitState.CLOSED.value)))
        last_failure_time = float(str(data.get("last_failure_time", 0.0)))

        if curr_state == CircuitState.OPEN:
            now = time.monotonic()
            if now - last_failure_time >= self._recovery_timeout:
                curr_state = CircuitState.HALF_OPEN
                data["state"] = curr_state.value
                self._save_data(name, data)

        return curr_state

    def allow_execution(self, name: str) -> bool:
        """Check if execution is permitted."""
        st = self.state(name)
        return st in (CircuitState.CLOSED, CircuitState.HALF_OPEN)

    def record_success(self, name: str) -> None:
        """Record a successful execution."""
        data = self._get_data(name)
        data["state"] = CircuitState.CLOSED.value
        data["failure_count"] = 0
        self._save_data(name, data)

    def record_failure(self, name: str, exc: Exception | None = None) -> None:
        """Record a failed execution."""
        data = self._get_data(name)
        curr_state = CircuitState(str(data.get("state", CircuitState.CLOSED.value)))
        failures = int(str(data.get("failure_count", 0))) + 1

        data["failure_count"] = failures
        data["last_failure_time"] = time.monotonic()

        if curr_state == CircuitState.HALF_OPEN or failures >= self._failure_threshold:
            data["state"] = CircuitState.OPEN.value

        self._save_data(name, data)

    def reset(self, name: str) -> None:
        """Reset named breaker."""
        self._cache.delete(self._key(name))

    def call(
        self, name: str, func: Callable[..., T], *args: object, **kwargs: object
    ) -> T:
        """Execute a callable with circuit breaker protection."""
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


class AsyncCacheCircuitBreaker(AsyncCircuitBreakerPort):
    """Distributed asynchronous circuit breaker adapter backed by AsyncCachePort."""

    def __init__(
        self,
        cache: AsyncCachePort,
        failure_threshold: int = 5,
        recovery_timeout_seconds: float = 10.0,
        key_prefix: str = "hexastack:circuit_breaker:",
    ) -> None:
        """Initialize async cache-backed circuit breaker."""
        self._cache = cache
        self._failure_threshold = max(1, failure_threshold)
        self._recovery_timeout = max(0.001, recovery_timeout_seconds)
        self._prefix = key_prefix

    def _key(self, name: str) -> str:
        return f"{self._prefix}{name}"

    async def _get_data(self, name: str) -> dict[str, object]:
        raw = await self._cache.get_async(self._key(name))
        if isinstance(raw, dict):
            return dict(raw)
        return {
            "state": CircuitState.CLOSED.value,
            "failure_count": 0,
            "last_failure_time": 0.0,
        }

    async def _save_data(self, name: str, data: dict[str, object]) -> None:
        ttl = self._recovery_timeout * 3
        await self._cache.set_async(self._key(name), data, ttl_seconds=ttl)

    async def state_async(self, name: str) -> CircuitState:
        """Get current operational state asynchronously."""
        data = await self._get_data(name)
        curr_state = CircuitState(str(data.get("state", CircuitState.CLOSED.value)))
        last_failure_time = float(str(data.get("last_failure_time", 0.0)))

        if curr_state == CircuitState.OPEN:
            now = time.monotonic()
            if now - last_failure_time >= self._recovery_timeout:
                curr_state = CircuitState.HALF_OPEN
                data["state"] = curr_state.value
                await self._save_data(name, data)

        return curr_state

    async def allow_execution_async(self, name: str) -> bool:
        """Check if execution is permitted asynchronously."""
        st = await self.state_async(name)
        return st in (CircuitState.CLOSED, CircuitState.HALF_OPEN)

    async def record_success_async(self, name: str) -> None:
        """Record successful execution asynchronously."""
        data = await self._get_data(name)
        data["state"] = CircuitState.CLOSED.value
        data["failure_count"] = 0
        await self._save_data(name, data)

    async def record_failure_async(
        self, name: str, exc: Exception | None = None
    ) -> None:
        """Record failed execution asynchronously."""
        data = await self._get_data(name)
        curr_state = CircuitState(str(data.get("state", CircuitState.CLOSED.value)))
        failures = int(str(data.get("failure_count", 0))) + 1

        data["failure_count"] = failures
        data["last_failure_time"] = time.monotonic()

        if curr_state == CircuitState.HALF_OPEN or failures >= self._failure_threshold:
            data["state"] = CircuitState.OPEN.value

        await self._save_data(name, data)

    async def reset_async(self, name: str) -> None:
        """Reset breaker state asynchronously."""
        await self._cache.delete_async(self._key(name))

    async def call_async(
        self,
        name: str,
        func: Callable[..., Awaitable[T]],
        *args: object,
        **kwargs: object,
    ) -> T:
        """Execute an async coroutine with circuit breaker protection."""
        if not await self.allow_execution_async(name):
            msg = f"Circuit breaker '{name}' is OPEN. Async call rejected."
            raise CircuitBreakerOpenError(msg)

        try:
            result = await func(*args, **kwargs)
            await self.record_success_async(name)
            return result
        except Exception as exc:
            await self.record_failure_async(name, exc)
            raise


__all__ = [
    "AsyncCacheCircuitBreaker",
    "CacheCircuitBreaker",
]
