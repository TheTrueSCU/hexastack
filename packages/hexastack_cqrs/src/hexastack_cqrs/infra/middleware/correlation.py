import inspect
from collections.abc import Callable
from typing import Any, cast

from hexastack_core.domain import Generic
from hexastack_core.utils.context import (
    get_correlation_id,
    new_correlation_id,
    set_correlation_id,
)


class CorrelationMiddleware:
    """Middleware establishing and propagating correlation IDs across message execution.

    Notes/Architectural Intent:
        Extracts correlation_id from incoming message attributes if present, or initializes
        a new correlation ID in the execution context, ensuring continuous tracing across handlers.
        Supports both synchronous handlers and asynchronous coroutines.
    """

    def __init__(self, generate_if_missing: bool = True) -> None:
        """Initialize CorrelationMiddleware.

        Args:
            generate_if_missing: If True, automatically generates a new UUID when no correlation ID exists.
        """
        self._generate_if_missing = generate_if_missing

    def __call__[G: Generic, R](self, instance: G, next_call: Callable[[G], R]) -> R:
        """Propagate or initialize correlation ID for message execution.

        Args:
            instance: The command, query, or event Generic instance.
            next_call: Callable representing the downstream middleware/handler chain.

        Returns:
            The handler execution result of type R (or coroutine if next_call is async).

        Raises:
            Exception: Propagates unhandled exceptions raised by downstream handlers.
        """
        existing_msg_cid = getattr(instance, "correlation_id", None)

        if existing_msg_cid:
            set_correlation_id(str(existing_msg_cid))
        elif not get_correlation_id() and self._generate_if_missing:
            new_correlation_id()

        result = next_call(instance)

        if inspect.iscoroutine(result):

            async def _async_wrapped() -> Any:
                return await result

            return cast(R, _async_wrapped())

        return result
