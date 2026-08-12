from abc import ABC, abstractmethod
from typing import TypeVar

E = TypeVar("E")
ID = TypeVar("ID")


class Repository[E, ID](ABC):
    """Abstract port interface for generic entity persistence repositories.

    Notes/Architectural Intent:
        Abstracts persistence mechanisms (SQL, NoSQL, memory) away from domain logic.
    """

    @abstractmethod
    def add(self, entity: E) -> None:
        """Add an entity instance to the repository storage.

        Args:
            entity: The domain entity object to persist.

        Returns:
            None.

        Raises:
            ValueError: If entity addition fails.
        """
        ...

    @abstractmethod
    def get_by_id(self, entity_id: ID) -> E | None:
        """Retrieve an entity instance by its unique identifier entity_id.

        Args:
            entity_id: The unique identifier.

        Returns:
            The entity instance if found, otherwise None.

        Raises:
            ValueError: If retrieval fails.
        """
        ...

    @abstractmethod
    def remove(self, entity_id: ID) -> None:
        """Remove an entity instance by its unique identifier entity_id.

        Args:
            entity_id: The unique identifier.

        Returns:
            None.

        Raises:
            ValueError: If removal fails.
        """
        ...
