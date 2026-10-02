"""Circuit Breaker CQRS Middleware providing fail-fast protection."""

from __future__ import annotations

import inspect
from collections.abc import Callable
from typing import Any, TypeVar

from hexastack_core.domain import Generic
from hexastack_core.domain.exceptions import CircuitBreakerOpenError
from hexastack_core.ports.circuit_breaker import (
    AsyncCircuitBreakerPort,
    CircuitBreakerPort,
)
from hexastack_core.ports.logging import LoggingPort
from hexastack_cqrs.infra.config import CircuitBreakerMiddlewareConfig
from hexastack_cqrs.infra.middleware.generic import InOutMiddleware

G = TypeVar("G", bound=Generic)


class CircuitBreakerMiddleware(InOutMiddleware):
    """CQRS middleware protecting command and query dispatch via CircuitBreakerPort.

    Notes/Architectural Intent:
        Intercepts message execution, evaluating breaker trip states per message class.
        Fails fast if the breaker is OPEN. Extends InOutMiddleware template.
    """

    def __init__(
        self,
        breaker: CircuitBreakerPort | None = None,
        config: CircuitBreakerMiddlewareConfig | None = None,
        logger: LoggingPort | None = None,
    ) -> None:
        """Initialize circuit breaker middleware.

        Args:
            breaker: CircuitBreakerPort instance used for state management.
            config: Optional CircuitBreakerMiddlewareConfig instance.
            logger: Optional LoggingPort instance for circuit transition logs.
        """
        self._breaker = breaker
        self._config = config or CircuitBreakerMiddlewareConfig()
        self._logger = logger

    def before(self, instance: Generic) -> Any:
        """Evaluate circuit breaker state before executing handler.

        Args:
            instance: Dispatched command or query message.

        Returns:
            The message name identifier.

        Raises:
            CircuitBreakerOpenError: If the circuit breaker is OPEN.
        """
        if not self._config.enable or self._breaker is None:
            return None

        name = instance.__class__.__name__
        if not self._breaker.allow_execution(name):
            if self._logger:
                self._logger.warning(
                    f"Circuit breaker for '{name}' is OPEN. Rejecting execution.",
                    extra={"message_type": name, "circuit_state": "open"},
                )
            msg = f"Circuit breaker for '{name}' is OPEN. Execution rejected."
            raise CircuitBreakerOpenError(msg)

        return name

    def after(self, instance: Generic, result: Any, context: Any) -> Any:
        """Record successful execution on the circuit breaker.

        Args:
            instance: Dispatched command or query message.
            result: Result of handler execution.
            context: Identifier returned by before().

        Returns:
            Unmodified result.
        """
        if self._breaker is not None and context is not None:
            self._breaker.record_success(str(context))
        return result

    def on_error(self, instance: Generic, exc: Exception, context: Any) -> None:
        """Record execution failure on the circuit breaker.

        Args:
            instance: Dispatched command or query message.
            exc: Exception raised during handler execution.
            context: Identifier returned by before().
        """
        if self._breaker is not None and context is not None:
            self._breaker.record_failure(str(context), exc)
            if self._logger:
                self._logger.error(
                    f"Circuit breaker recorded failure for '{context}': {exc}",
                    extra={"message_type": str(context), "error": str(exc)},
                )


class AsyncCircuitBreakerMiddleware:
    """Async-native CQRS middleware protecting asynchronous coroutine execution."""

    def __init__(
        self,
        breaker: AsyncCircuitBreakerPort | None = None,
        config: CircuitBreakerMiddlewareConfig | None = None,
        logger: LoggingPort | None = None,
    ) -> None:
        """Initialize async circuit breaker middleware.

        Args:
            breaker: AsyncCircuitBreakerPort instance used for state management.
            config: Optional CircuitBreakerMiddlewareConfig instance.
            logger: Optional LoggingPort instance.
        """
        self._breaker = breaker
        self._config = config or CircuitBreakerMiddlewareConfig()
        self._logger = logger

    async def __call__(
        self,
        instance: G,
        next_call: Callable[[G], Any],
    ) -> Any:
        """Execute next_call wrapped with async circuit breaker protection.

        Args:
            instance: Dispatched command or query message.
            next_call: Downstream handler execution callable.

        Returns:
            Result returned by next_call.

        Raises:
            CircuitBreakerOpenError: If breaker is OPEN.
        """
        if not self._config.enable or self._breaker is None:
            res = next_call(instance)
            if inspect.isawaitable(res):
                return await res
            return res

        name = instance.__class__.__name__
        if not await self._breaker.allow_execution_async(name):
            if self._logger:
                self._logger.warning(
                    f"Async circuit breaker for '{name}' is OPEN. Rejecting execution.",
                    extra={"message_type": name, "circuit_state": "open"},
                )
            msg = f"Async circuit breaker for '{name}' is OPEN. Execution rejected."
            raise CircuitBreakerOpenError(msg)

        try:
            res = next_call(instance)
            if inspect.isawaitable(res):
                result = await res
            else:
                result = res
            await self._breaker.record_success_async(name)
            return result
        except Exception as exc:
            await self._breaker.record_failure_async(name, exc)
            if self._logger:
                self._logger.error(
                    f"Async circuit breaker recorded failure for '{name}': {exc}",
                    extra={"message_type": name, "error": str(exc)},
                )
            raise


__all__ = [
    "AsyncCircuitBreakerMiddleware",
    "CircuitBreakerMiddleware",
]
