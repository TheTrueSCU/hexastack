"""Circuit Breaker port contracts defining state transitions and execution guards."""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Awaitable, Callable
from enum import StrEnum
from typing import TypeVar

T = TypeVar("T")


class CircuitState(StrEnum):
    """Enumeration representing the runtime operational state of a circuit breaker.

    Notes/Architectural Intent:
        Follows standard resilience state machine topology:
        - CLOSED: Normal operation. All calls allowed through. Failures are tracked.
        - OPEN: Fault state. Calls fail fast with CircuitBreakerOpenError without invoking target.
        - HALF_OPEN: Trial recovery state. A limited capacity of trial calls are permitted to probe recovery.
    """

    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"


class CircuitBreakerPort(ABC):
    """Abstract port defining synchronous circuit breaker lifecycle and execution protection.

    Notes/Architectural Intent:
        Decouples commands, queries, external HTTP/gRPC adapters, and database gateways
        from specific breaker storage engines (In-Memory, Redis CachePort, etc.).
    """

    @abstractmethod
    def state(self, name: str) -> CircuitState:
        """Get the current operational state of a named circuit breaker.

        Args:
            name: Identifier for the circuit breaker.

        Returns:
            The current CircuitState (CLOSED, OPEN, or HALF_OPEN).
        """

    @abstractmethod
    def allow_execution(self, name: str) -> bool:
        """Check if a call is allowed through the circuit breaker.

        Args:
            name: Identifier for the circuit breaker.

        Returns:
            True if execution is permitted, False if the breaker is OPEN and rejecting calls.
        """

    @abstractmethod
    def record_success(self, name: str) -> None:
        """Record a successful execution for a named circuit breaker.

        Args:
            name: Identifier for the circuit breaker.
        """

    @abstractmethod
    def record_failure(self, name: str, exc: Exception | None = None) -> None:
        """Record a failed execution for a named circuit breaker.

        Args:
            name: Identifier for the circuit breaker.
            exc: Optional exception that triggered the failure.
        """

    @abstractmethod
    def reset(self, name: str) -> None:
        """Reset a named circuit breaker back to CLOSED state and zero error counts.

        Args:
            name: Identifier for the circuit breaker.
        """

    @abstractmethod
    def call(
        self, name: str, func: Callable[..., T], *args: object, **kwargs: object
    ) -> T:
        """Execute a callable protected by the circuit breaker.

        Args:
            name: Identifier for the circuit breaker.
            func: Target callable to execute.
            *args: Positional arguments for func.
            **kwargs: Keyword arguments for func.

        Returns:
            The result of func(*args, **kwargs).

        Raises:
            CircuitBreakerOpenError: If the breaker is OPEN and rejects the call.
        """


class AsyncCircuitBreakerPort(ABC):
    """Abstract port defining asynchronous circuit breaker lifecycle and execution protection.

    Notes/Architectural Intent:
        Async-native counterpart to CircuitBreakerPort for non-blocking coroutine execution.
    """

    @abstractmethod
    async def state_async(self, name: str) -> CircuitState:
        """Get the current operational state of a named circuit breaker asynchronously.

        Args:
            name: Identifier for the circuit breaker.

        Returns:
            The current CircuitState.
        """

    @abstractmethod
    async def allow_execution_async(self, name: str) -> bool:
        """Check if a call is allowed through the circuit breaker asynchronously.

        Args:
            name: Identifier for the circuit breaker.

        Returns:
            True if execution is permitted, False if rejecting.
        """

    @abstractmethod
    async def record_success_async(self, name: str) -> None:
        """Record a successful execution asynchronously.

        Args:
            name: Identifier for the circuit breaker.
        """

    @abstractmethod
    async def record_failure_async(
        self, name: str, exc: Exception | None = None
    ) -> None:
        """Record a failed execution asynchronously.

        Args:
            name: Identifier for the circuit breaker.
            exc: Optional exception that triggered the failure.
        """

    @abstractmethod
    async def reset_async(self, name: str) -> None:
        """Reset a named circuit breaker asynchronously back to CLOSED state.

        Args:
            name: Identifier for the circuit breaker.
        """

    @abstractmethod
    async def call_async(
        self,
        name: str,
        func: Callable[..., Awaitable[T]],
        *args: object,
        **kwargs: object,
    ) -> T:
        """Execute an async coroutine callable protected by the circuit breaker.

        Args:
            name: Identifier for the circuit breaker.
            func: Target async callable to execute.
            *args: Positional arguments for func.
            **kwargs: Keyword arguments for func.

        Returns:
            The result of await func(*args, **kwargs).

        Raises:
            CircuitBreakerOpenError: If the breaker is OPEN and rejects the call.
        """


__all__ = [
    "AsyncCircuitBreakerPort",
    "CircuitBreakerPort",
    "CircuitState",
]
