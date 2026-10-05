from abc import ABC, abstractmethod
from typing import Any

from hexastack_core.domain import Command, Event, Query


class GenericHandler[I, R](ABC):
    """Abstract base class for generic message handlers.

    Notes/Architectural Intent:
        Establishes single-method `handle(item)` contract for processing commands, events, and queries.
    """

    @abstractmethod
    def handle(self, item: I) -> R:
        """Process item and return result of type R.

        Args:
            item: Input message instance.

        Returns:
            The handler execution output.

        Raises:
            Exception: Any exception raised during message processing.
        """


class CommandHandler[C: Command, R](GenericHandler[C, R]):
    """Base class for Command handling logic.

    Notes/Architectural Intent:
        Processes state-changing commands and returns execution result or Result[T].
    """


class EventHandler[E: Event](GenericHandler[E, None]):
    """Base class for Event notification handling logic.

    Notes/Architectural Intent:
        Processes domain event notifications asynchronously or synchronously without returning data.
    """


class QueryHandler[Q: Query[Any], R](GenericHandler[Q, R]):
    """Base class for Query handling logic.

    Notes/Architectural Intent:
        Executes read-only queries and returns data view models or DTOs.
    """
