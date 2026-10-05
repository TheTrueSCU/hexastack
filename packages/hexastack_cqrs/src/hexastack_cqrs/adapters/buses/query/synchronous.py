from collections.abc import Callable
from typing import Any

from hexastack_core.domain import Generic, Query
from hexastack_cqrs.ports.buses import (
    HandlerDispatcherPort,
    MiddlewarePort,
    QueryBusPort,
)


class SynchronousQueryBus(QueryBusPort):
    """Synchronous in-process QueryBus dispatching queries through a middleware pipeline.

    Notes/Architectural Intent:
        Executes query handlers synchronously with onion-layered middleware support,
        returning structured query results to caller.
    """

    def __init__(
        self,
        handler_registry: HandlerDispatcherPort,
        middleware: list[MiddlewarePort] | None = None,
    ) -> None:
        """Initialize synchronous query bus with handler registry and middleware.

        Args:
            handler_registry: HandlerDispatcherPort containing registered query handlers.
            middleware: Optional ordered list of MiddlewarePort interceptors.
        """
        self._registry = handler_registry
        self._middleware = list(middleware) if middleware is not None else []

    def dispatch(self, query: Query[Any]) -> Any:
        """Dispatch a Query through the middleware pipeline to its registered handler.

        Args:
            query: The query instance to dispatch.

        Returns:
            The query result returned by the query handler.

        Raises:
            HandlerRegistryError: If no handler is registered for query.
            Exception: Propagates unhandled exceptions or domain errors raised during execution.
        """
        pipeline: Callable[[Generic], Any] = lambda inst: self._registry.handle(
            inst, reraise=True
        )

        for mw in reversed(self._middleware):
            next_fn = pipeline
            pipeline = lambda inst, m=mw, n=next_fn: m(inst, n)

        return pipeline(query)
