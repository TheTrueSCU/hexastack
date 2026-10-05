import inspect
from collections.abc import Callable
from typing import Any, Protocol, cast

from hexastack_core.domain import Generic
from hexastack_cqrs.ports.buses import MiddlewarePort


class GenericMiddleware(Protocol):
    """Protocol defining the interface for CQRS middleware components.

    Notes/Architectural Intent:
        Middleware wraps handler invocation to intercept processing, apply cross-cutting
        concerns (e.g. retry, logging, validation), and pass control down the execution chain.
    """

    def __call__[G: Generic, R](
        self,
        instance: G,
        next_call: Callable[[G], R],
    ) -> R:
        """Invoke middleware logic and pass execution to next_call.

        Args:
            instance: The command or query message instance.
            next_call: Callable representing the remaining middleware/handler chain.

        Returns:
            The result returned from downstream processing.

        Raises:
            Exception: Re-raises unhandled exceptions or domain errors.
        """


class InOutMiddleware(MiddlewarePort):
    """Base class for CQRS middleware with before, after, and error lifecycle hooks.

    Notes/Architectural Intent:
        Implements the Template Method pattern over MiddlewarePort. Subclasses
        override before(), after(), and/or on_error() hooks without needing to
        manage synchronous vs. asynchronous coroutine unwrapping and closure wrapping.
    """

    def before(self, instance: Generic) -> Any:
        """Pre-execution hook executed before downstream processing.

        Args:
            instance: Dispatched command, query, or event message.

        Returns:
            Optional context object passed to subsequent after() and on_error() hooks.

        Notes/Architectural Intent:
            Subclasses override this to perform pre-processing (e.g. starting timers,
            opening tracing spans, setting context variables).
        """
        return None

    def after(self, instance: Generic, result: Any, context: Any) -> Any:
        """Post-execution hook executed after successful handler completion.

        Args:
            instance: Dispatched command, query, or event message.
            result: Result returned by downstream handler.
            context: Context object returned by before().

        Returns:
            The final result returned to the caller (can transform result if needed).

        Notes/Architectural Intent:
            Subclasses override this to perform post-processing (e.g. logging success,
            capturing emitted events, recording duration).
        """
        return result

    def on_error(self, instance: Generic, exc: Exception, context: Any) -> None:
        """Error hook executed when downstream execution raises an unhandled exception.

        Args:
            instance: Dispatched command, query, or event message.
            exc: Exception raised by downstream handler.
            context: Context object returned by before().

        Notes/Architectural Intent:
            Subclasses override this to perform error logging, telemetry exception
            recording, or transactional cleanups before the exception is re-raised.
        """

    def __call__[G: Generic, R](self, instance: G, next_call: Callable[[G], R]) -> R:
        """Execute template lifecycle wrapping next_call.

        Args:
            instance: Dispatched message instance.
            next_call: Next middleware or handler in chain.

        Returns:
            Result returned by after() or an async coroutine wrapping the execution.

        Raises:
            Exception: Propagates unhandled exceptions raised during execution.
        """
        context = self.before(instance)
        try:
            result = next_call(instance)
        except Exception as exc:
            self.on_error(instance, exc, context)
            raise

        if inspect.isawaitable(result):

            async def _async_wrap() -> Any:
                try:
                    res = await result
                    return self.after(instance, res, context)
                except Exception as async_exc:
                    self.on_error(instance, async_exc, context)
                    raise

            return cast("R", _async_wrap())

        return cast("R", self.after(instance, result, context))


__all__ = [
    "GenericMiddleware",
    "InOutMiddleware",
]
