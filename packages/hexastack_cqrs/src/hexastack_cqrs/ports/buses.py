from abc import ABC, abstractmethod
from typing import Any

from hexastack_core.domain import Command, Event, Query


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
