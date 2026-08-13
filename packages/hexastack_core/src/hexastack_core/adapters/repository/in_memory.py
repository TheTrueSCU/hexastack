from collections.abc import Callable

from hexastack_core.ports.repository import (
    AsyncRepositoryPort,
    RepositoryPort,
)


class InMemoryRepository[E, ID](RepositoryPort[E, ID]):
    """Generic in-memory repository adapter storing entities in a dictionary.

    Notes/Architectural Intent:
        Serves as a built-in repository adapter for fast unit testing, local prototyping,
        and lightweight in-memory storage without external database infrastructure dependencies.
    """

    def __init__(
        self,
        id_getter: Callable[[E], ID] | None = None,
        id_attr: str = "id",
    ) -> None:
        """Initialize empty in-memory repository.

        Args:
            id_getter: Optional custom callable to extract the ID from an entity.
            id_attr: Attribute name to extract if id_getter is not supplied. Defaults to "id".
        """
        self._store: dict[ID, E] = {}
        self._id_getter: Callable[[E], ID] = (
            id_getter
            if id_getter is not None
            else (lambda entity: getattr(entity, id_attr))
        )

    def add(self, entity: E) -> None:
        """Add or update an entity in the repository store.

        Args:
            entity: Domain entity to persist.

        Returns:
            None.

        Raises:
            AttributeError: If entity lacks the configured id attribute and no id_getter was provided.
        """
        entity_id = self._id_getter(entity)
        self._store[entity_id] = entity

    def all(self) -> list[E]:
        """Retrieve all persisted entities currently in the store.

        Returns:
            List of all stored entity instances.

        Raises:
            None.
        """
        return list(self._store.values())

    def clear(self) -> None:
        """Clear all stored entities from the repository.

        Returns:
            None.

        Raises:
            None.
        """
        self._store.clear()

    def get_by_id(self, entity_id: ID) -> E | None:
        """Retrieve an entity by its identifier.

        Args:
            entity_id: The unique identifier.

        Returns:
            The entity instance if found, otherwise None.

        Raises:
            None.
        """
        return self._store.get(entity_id)

    def remove(self, entity_id: ID) -> None:
        """Remove an entity by its identifier.

        Args:
            entity_id: The unique identifier.

        Returns:
            None.

        Raises:
            None.
        """
        self._store.pop(entity_id, None)


class AsyncInMemoryRepository[E, ID](AsyncRepositoryPort[E, ID]):
    """Generic asynchronous in-memory repository adapter.

    Notes/Architectural Intent:
        Implements AsyncRepositoryPort[E, ID] for asynchronous workflows (FastAPI,
        gRPC, async CQRS) without external database dependencies.
    """

    def __init__(
        self,
        id_getter: Callable[[E], ID] | None = None,
        id_attr: str = "id",
    ) -> None:
        self._sync_repo = InMemoryRepository[E, ID](
            id_getter=id_getter, id_attr=id_attr
        )

    async def add_async(self, entity: E) -> None:
        """Asynchronously add or update an entity."""
        self._sync_repo.add(entity)

    async def get_by_id_async(self, entity_id: ID) -> E | None:
        """Asynchronously retrieve an entity by ID."""
        return self._sync_repo.get_by_id(entity_id)

    async def all_async(self) -> list[E]:
        """Asynchronously retrieve all entities."""
        return self._sync_repo.all()

    async def remove_async(self, entity_id: ID) -> None:
        """Asynchronously remove an entity by ID."""
        self._sync_repo.remove(entity_id)

    def clear(self) -> None:
        """Clear all stored entities."""
        self._sync_repo.clear()


__all__ = [
    "AsyncInMemoryRepository",
    "InMemoryRepository",
]
