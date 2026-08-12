from collections.abc import Callable
from concurrent.futures import Future, ThreadPoolExecutor
from typing import Any

from hexastack_core.domain import Event, Generic
from huey import Huey

from hexastack_cqrs.infra.middleware.generic import GenericMiddleware
from hexastack_cqrs.ports.buses import EventBusPort


class HueyEventBus(EventBusPort):
    """Asynchronous EventBus adapter broadcasting domain events via Huey task queue.

    Notes/Architectural Intent:
        Dispatches domain events to background worker processes via Huey tasks,
        executing each subscriber independently and asynchronously across worker threads/processes.
    """

    def __init__(
        self,
        huey: Huey,
        middleware: list[GenericMiddleware] | None = None,
    ) -> None:
        """Initialize Huey event bus with Huey instance and optional middleware.

        Args:
            huey: Initialized Huey task queue instance.
            middleware: Optional ordered list of GenericMiddleware interceptors.
        """
        self._huey = huey
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

    def publish(self, event: Event) -> list[Any]:
        """Publish event by enqueuing an asynchronous task for each registered subscriber.

        Args:
            event: The domain event instance to broadcast.

        Returns:
            List of Huey Task instances representing scheduled background subscriber jobs.

        Raises:
            Exception: If enqueuing tasks to Huey queue fails.
        """
        target_handlers = self.handlers(type(event))
        tasks: list[Any] = []

        for handler in target_handlers:
            @self._huey.task()
            def _execute_subscriber(evt: Event, h: Callable[[Any], None] = handler) -> None:
                pipeline: Callable[[Generic], Any] = lambda inst: h(inst)
                for mw in reversed(self._middleware):
                    next_fn = pipeline
                    pipeline = lambda inst, m=mw, n=next_fn: m(inst, n)
                pipeline(evt)

            task = _execute_subscriber(event)
            tasks.append(task)

        return tasks

    def subscribe(
        self, event_cls: type[Event], handler: Callable[[Any], None]
    ) -> None:
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


class NativeAsyncEventBus(EventBusPort):
    """Asynchronous in-process EventBus using thread pool execution.

    Notes/Architectural Intent:
        Broadcasts domain events to registered subscribers asynchronously on worker threads,
        returning Futures without requiring external queue backends.
    """

    def __init__(
        self,
        middleware: list[GenericMiddleware] | None = None,
        executor: ThreadPoolExecutor | None = None,
    ) -> None:
        """Initialize native async event bus.

        Args:
            middleware: Optional ordered list of GenericMiddleware interceptors.
            executor: Optional ThreadPoolExecutor for managing worker threads.
        """
        self._middleware = list(middleware) if middleware is not None else []
        self._subscribers: dict[type[Event], list[Callable[[Any], None]]] = {}
        self._executor = executor or ThreadPoolExecutor(thread_name_prefix="cqrs-event-async")

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

    def publish(self, event: Event) -> list[Future[None]]:
        """Publish event asynchronously by dispatching each subscriber to the thread pool.

        Args:
            event: The domain event instance to broadcast.

        Returns:
            List of Future objects corresponding to subscriber executions.

        Raises:
            Exception: If submitting tasks to executor fails.
        """
        target_handlers = self.handlers(type(event))
        futures: list[Future[None]] = []

        for handler in target_handlers:
            def _run_subscriber(h: Callable[[Any], None] = handler) -> None:
                pipeline: Callable[[Generic], Any] = lambda inst: h(inst)
                for mw in reversed(self._middleware):
                    next_fn = pipeline
                    pipeline = lambda inst, m=mw, n=next_fn: m(inst, n)
                pipeline(event)

            future = self._executor.submit(_run_subscriber)
            futures.append(future)

        return futures

    def subscribe(
        self, event_cls: type[Event], handler: Callable[[Any], None]
    ) -> None:
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
