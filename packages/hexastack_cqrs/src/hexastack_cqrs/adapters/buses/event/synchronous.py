from collections.abc import Callable
from typing import Any

from hexastack_core.domain import Event, Generic

from hexastack_cqrs.infra.middleware.generic import GenericMiddleware
from hexastack_cqrs.ports.buses import EventBusPort


class SynchronousEventBus(EventBusPort):
    """Synchronous in-process EventBus dispatching domain events to subscribed handlers.

    Notes/Architectural Intent:
        Allows 1-to-many subscription mapping for domain events, executing each subscriber
        in-process with optional middleware chain execution per handler invocation.
    """

    def __init__(self, middleware: list[GenericMiddleware] | None = None) -> None:
        """Initialize synchronous event bus with optional middleware pipeline.

        Args:
            middleware: Optional ordered list of GenericMiddleware interceptors.
        """
        self._middleware = list(middleware) if middleware is not None else []
        self._subscribers: dict[type[Event], list[Callable[[Any], None]]] = {}

    def clear(self) -> None:
        """Clear all event subscriptions from the bus.

        Returns:
            None.

        Raises:
            None.
        """
        self._subscribers.clear()

    def handlers(self, event_cls: type[Event]) -> list[Callable[[Any], None]]:
        """Retrieve all subscribed handler callables for an event class and its superclasses.

        Args:
            event_cls: Target event class type.

        Returns:
            List of matching handler callables in subscription order.

        Raises:
            None.
        """
        matched: list[Callable[[Any], None]] = []
        for registered_cls, handler_list in self._subscribers.items():
            if issubclass(event_cls, registered_cls):
                matched.extend(handler_list)
        return matched

    def publish(self, event: Event) -> None:
        """Publish a domain event to all matching registered subscriber handlers.

        Args:
            event: The domain event instance to broadcast.

        Returns:
            None.

        Raises:
            Exception: Propagates unhandled exceptions raised by event subscriber handlers.
        """
        target_handlers = self.handlers(type(event))

        for handler in target_handlers:
            pipeline: Callable[[Generic], Any] = lambda inst, h=handler: h(inst)

            for mw in reversed(self._middleware):
                next_fn = pipeline
                pipeline = lambda inst, m=mw, n=next_fn: m(inst, n)

            pipeline(event)

    def subscribe(self, event_cls: type[Event], handler: Callable[[Any], None]) -> None:
        """Subscribe a handler callable to receive events of type event_cls.

        Args:
            event_cls: The Event class type to subscribe to.
            handler: Callable invoked when an event matching event_cls is published.

        Returns:
            None.

        Raises:
            None.
        """
        if event_cls not in self._subscribers:
            self._subscribers[event_cls] = []
        self._subscribers[event_cls].append(handler)
