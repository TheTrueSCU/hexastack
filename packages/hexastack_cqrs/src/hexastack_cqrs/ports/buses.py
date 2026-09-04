from abc import ABC, abstractmethod
from collections.abc import Callable
from typing import Any, Protocol, runtime_checkable

from hexastack_core.domain import Command, Event, Generic, Query

__all__ = [
    "CommandBusPort",
    "EventBusPort",
    "HandlerDispatcherPort",
    "MiddlewarePort",
    "QueryBusPort",
]


class HandlerDispatcherPort(ABC):
    """Abstract interface defining message handler lookup and invocation operations.

    Notes/Architectural Intent:
        Establishes an inward-facing port for buses in the adapters layer to execute
        message handlers without directly importing concrete HandlerRegistry implementations
        from the infrastructure layer.
    """

    @abstractmethod
    def handle(
        self, instance: Generic, exact: bool = False, reraise: bool = True
    ) -> Any:
        """Execute the handler corresponding to the given message instance.

        Args:
            instance: Generic command, query, event, or exception message instance.
            exact: If True, requires an exact class match without subclass traversal.
            reraise: If True, raises when no handler is found.

        Returns:
            The handler execution result, or None if unhandled and reraise=False.

        Raises:
            Exception: If no handler is registered (and reraise=True) or if the handler fails.
        """
        ...


@runtime_checkable
class MiddlewarePort(Protocol):
    """Protocol interface defining CQRS pipeline middleware interceptors.

    Notes/Architectural Intent:
        Establishes an onion-layered interceptor contract for commands, queries, and events.
        Decouples bus adapters from concrete middleware classes in the infrastructure layer.
        Using Protocol enables functions, lambdas, and classes with __call__ to seamlessly
        satisfy the port contract.
    """

    def __call__[G: Generic, R](
        self,
        instance: G,
        next_call: Callable[[G], R],
    ) -> R:
        """Invoke middleware logic and pass execution to next_call.

        Args:
            instance: Dispatched message instance.
            next_call: Callable representing the remaining middleware/handler chain.

        Returns:
            The result returned from downstream processing.

        Raises:
            Exception: Re-raises unhandled exceptions or domain errors.
        """
        ...


class CommandBusPort(ABC):
    """Abstract interface defining command dispatching operations.

    Notes/Architectural Intent:
        Decouples command initiation from command handler execution, allowing middleware,
        retry loops, and transaction management to wrap execution cleanly.
    """

    @abstractmethod
    def dispatch(self, command: Command) -> Any:
        """Dispatch a Command to its registered handler.

        Args:
            command: The command object to dispatch.

        Returns:
            The handler execution result.

        Raises:
            CommandRegistryError: If no handler is registered for command.
        """
        ...


class EventBusPort(ABC):
    """Abstract interface defining domain event publication operations.

    Notes/Architectural Intent:
        Enables asynchronous or decoupled notification of domain state changes
        to zero or more event listeners.
    """

    @abstractmethod
    def publish(self, event: Event) -> Any:
        """Publish a domain Event to registered event handlers.

        Args:
            event: The domain event instance to publish.

        Returns:
            Publication outcome, background task references, or None.

        Raises:
            None.
        """
        ...


class QueryBusPort(ABC):
    """Abstract interface defining query execution operations.

    Notes/Architectural Intent:
        Decouples read-side query formulation from data retrieval and view modeling handlers.
    """

    @abstractmethod
    def dispatch(self, query: Query[Any]) -> Any:
        """Dispatch a Query to its registered handler.

        Args:
            query: The query object to dispatch.

        Returns:
            The query result returned by the query handler.

        Raises:
            QueryRegistryError: If no handler is registered for query.
        """
        ...
