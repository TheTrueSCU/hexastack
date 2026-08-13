from abc import ABC, abstractmethod
from typing import TypeVar

E = TypeVar("E")
ID = TypeVar("ID")


class RepositoryPort[E, ID](ABC):
    """Abstract port interface for generic synchronous entity persistence repositories.

    Notes/Architectural Intent:
        Abstracts persistence mechanisms (SQL, NoSQL, memory) away from domain logic.
    """

    @abstractmethod
    def add(self, entity: E) -> None:
        """Add an entity instance to the repository storage."""
        ...

    @abstractmethod
    def get_by_id(self, entity_id: ID) -> E | None:
        """Retrieve an entity instance by its unique identifier."""
        ...

    @abstractmethod
    def remove(self, entity_id: ID) -> None:
        """Remove an entity instance by its unique identifier."""
        ...


class AsyncRepositoryPort[E, ID](ABC):
    """Abstract port interface for generic asynchronous entity persistence repositories."""

    @abstractmethod
    async def add_async(self, entity: E) -> None:
        """Asynchronously add an entity instance to the repository storage."""
        ...

    @abstractmethod
    async def get_by_id_async(self, entity_id: ID) -> E | None:
        """Asynchronously retrieve an entity instance by its unique identifier."""
        ...

    @abstractmethod
    async def remove_async(self, entity_id: ID) -> None:
        """Asynchronously remove an entity instance by its unique identifier."""
        ...


__all__ = [
    "AsyncRepositoryPort",
    "RepositoryPort",
]
