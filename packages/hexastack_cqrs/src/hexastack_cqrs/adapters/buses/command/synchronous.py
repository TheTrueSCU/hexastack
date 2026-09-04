from collections.abc import Callable
from typing import Any

from hexastack_core.domain import Command, Generic
from hexastack_cqrs.ports.buses import (
    CommandBusPort,
    HandlerDispatcherPort,
    MiddlewarePort,
)


class SynchronousCommandBus(CommandBusPort):
    """Synchronous in-process CommandBus dispatching commands through a middleware pipeline.

    Notes/Architectural Intent:
        Wraps command execution in an onion-layered middleware chain and dispatches
        to the registered handler in HandlerDispatcherPort.
    """

    def __init__(
        self,
        handler_registry: HandlerDispatcherPort,
        middleware: list[MiddlewarePort] | None = None,
    ) -> None:
        """Initialize synchronous command bus with handler registry and middleware.

        Args:
            handler_registry: HandlerDispatcherPort containing registered command handlers.
            middleware: Optional ordered list of MiddlewarePort interceptors.
        """
        self._registry = handler_registry
        self._middleware = list(middleware) if middleware is not None else []

    def dispatch(self, command: Command) -> Any:
        """Dispatch a Command through the middleware pipeline to its registered handler.

        Args:
            command: The command instance to dispatch.

        Returns:
            The handler execution result.

        Raises:
            HandlerRegistryError: If no handler is registered for command.
            Exception: Propagates unhandled exceptions or domain errors raised during execution.
        """
        pipeline: Callable[[Generic], Any] = lambda inst: self._registry.handle(
            inst, reraise=True
        )

        for mw in reversed(self._middleware):
            next_fn = pipeline
            pipeline = lambda inst, m=mw, n=next_fn: m(inst, n)

        return pipeline(command)
