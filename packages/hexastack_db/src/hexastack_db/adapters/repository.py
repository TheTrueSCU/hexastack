from collections.abc import Sequence
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Session

from hexastack_core.ports.repository import (
    AsyncRepositoryPort,
    RepositoryPort,
)
from hexastack_db.domain.exceptions import (
    DatabaseError,
    UniqueConstraintViolationError,
)


class SqlAlchemyRepository[T, ID](RepositoryPort[T, ID]):
    """SQLAlchemy implementation of the generic Repository port.

    Notes/Architectural Intent:
        Implements synchronous CRUD operations over declarative SQLAlchemy models,
        translating raw integrity errors into domain-level database exceptions.
    """

    def __init__(self, session: Session, model_cls: type[T]) -> None:
        """Initialize repository with active session and target model class.

        Args:
            session: Active SQLAlchemy Session instance.
            model_cls: Declarative SQLAlchemy model class.
        """
        self._session = session
        self._model_cls = model_cls

    def add(self, entity: T) -> None:
        """Persist a new entity to the database session.

        Args:
            entity: Domain model entity instance.

        Returns:
            None.

        Raises:
            UniqueConstraintViolationError: If a uniqueness constraint is violated.
            DatabaseError: If database persistence fails.
        """
        try:
            self._session.add(entity)
            self._session.flush()
        except IntegrityError as exc:
            raise UniqueConstraintViolationError(str(exc.orig or exc)) from exc
        except Exception as exc:
            raise DatabaseError(str(exc)) from exc

    def add_many(self, entities: Sequence[T]) -> None:
        """Persist multiple entities in batch.

        Args:
            entities: Sequence of entities to persist.

        Returns:
            None.

        Raises:
            UniqueConstraintViolationError: If a uniqueness constraint is violated.
            DatabaseError: If database persistence fails.
        """
        try:
            self._session.add_all(entities)
            self._session.flush()
        except IntegrityError as exc:
            raise UniqueConstraintViolationError(str(exc.orig or exc)) from exc
        except Exception as exc:
            raise DatabaseError(str(exc)) from exc

    def count(self, **filters: Any) -> int:
        """Return count of matching records.

        Args:
            **filters: Field-value filtering criteria.

        Returns:
            Total count of matching records.

        Raises:
            DatabaseError: If query execution fails.
        """
        try:
            stmt = select(func.count()).select_from(self._model_cls)
            for k, v in filters.items():
                if hasattr(self._model_cls, k):
                    stmt = stmt.where(getattr(self._model_cls, k) == v)
            result = self._session.scalar(stmt)
            return int(result or 0)
        except Exception as exc:
            raise DatabaseError(str(exc)) from exc

    def delete(self, entity_id: ID) -> bool:
        """Delete an entity by primary key.

        Args:
            entity_id: Primary key identifier.

        Returns:
            True if an entity was found and deleted, otherwise False.

        Raises:
            DatabaseError: If deletion fails.
        """
        try:
            entity = self._session.get(self._model_cls, entity_id)
            if entity is None:
                return False
            self._session.delete(entity)
            self._session.flush()
            return True
        except Exception as exc:
            raise DatabaseError(str(exc)) from exc

    def get(self, entity_id: ID) -> T | None:
        """Retrieve entity by primary key identifier.

        Args:
            entity_id: Primary key identifier.

        Returns:
            Entity instance if found, otherwise None.

        Raises:
            DatabaseError: If query execution fails.
        """
        return self.get_by_id(entity_id)

    def get_by_id(self, entity_id: ID) -> T | None:
        """Retrieve entity by unique identifier (satisfies Repository port).

        Args:
            entity_id: Primary key identifier.

        Returns:
            Entity instance if found, otherwise None.

        Raises:
            DatabaseError: If query execution fails.
        """
        try:
            return self._session.get(self._model_cls, entity_id)
        except Exception as exc:
            raise DatabaseError(str(exc)) from exc

    def list(self, offset: int = 0, limit: int = 100, **filters: Any) -> Sequence[T]:
        """Query a page of entities matching optional attribute filters.

        Args:
            offset: Pagination offset index.
            limit: Maximum number of records to return.
            **filters: Field-value filtering criteria.

        Returns:
            Sequence of matching entities.

        Raises:
            DatabaseError: If query execution fails.
        """
        try:
            stmt = select(self._model_cls).offset(offset).limit(limit)
            for k, v in filters.items():
                if hasattr(self._model_cls, k):
                    stmt = stmt.where(getattr(self._model_cls, k) == v)
            result = self._session.execute(stmt).scalars().all()
            return list(result)
        except Exception as exc:
            raise DatabaseError(str(exc)) from exc

    def remove(self, entity_id: ID) -> None:
        """Remove an entity instance by primary key (satisfies Repository port).

        Args:
            entity_id: Primary key identifier.

        Returns:
            None.

        Raises:
            DatabaseError: If deletion fails.
        """
        self.delete(entity_id)

    def update(self, entity: T) -> T:
        """Update an existing entity in the session.

        Args:
            entity: Modified entity instance.

        Returns:
            The merged entity instance.

        Raises:
            UniqueConstraintViolationError: If updating violates a constraint.
            DatabaseError: If update fails.
        """
        try:
            merged = self._session.merge(entity)
            self._session.flush()
            return merged
        except IntegrityError as exc:
            raise UniqueConstraintViolationError(str(exc.orig or exc)) from exc
        except Exception as exc:
            raise DatabaseError(str(exc)) from exc


class AsyncSqlAlchemyRepository[T, ID](AsyncRepositoryPort[T, ID]):
    """Asynchronous SQLAlchemy repository implementation.

    Notes/Architectural Intent:
        Implements async CRUD operations over AsyncSession for non-blocking I/O.
    """

    def __init__(self, session: AsyncSession, model_cls: type[T]) -> None:
        """Initialize async repository with AsyncSession and model class.

        Args:
            session: Active AsyncSession instance.
            model_cls: Declarative SQLAlchemy model class.
        """
        self._session = session
        self._model_cls = model_cls

    async def add(self, entity: T) -> None:
        """Persist a new entity asynchronously.

        Args:
            entity: Domain model entity instance.

        Returns:
            None.

        Raises:
            UniqueConstraintViolationError: If constraint violation occurs.
            DatabaseError: If persistence fails.
        """
        try:
            self._session.add(entity)
            await self._session.flush()
        except IntegrityError as exc:
            raise UniqueConstraintViolationError(str(exc.orig or exc)) from exc
        except Exception as exc:
            raise DatabaseError(str(exc)) from exc

    async def add_many(self, entities: Sequence[T]) -> None:
        """Persist multiple entities in batch asynchronously.

        Args:
            entities: Sequence of entities to persist.

        Returns:
            None.

        Raises:
            UniqueConstraintViolationError: If constraint violation occurs.
            DatabaseError: If persistence fails.
        """
        try:
            self._session.add_all(entities)
            await self._session.flush()
        except IntegrityError as exc:
            raise UniqueConstraintViolationError(str(exc.orig or exc)) from exc
        except Exception as exc:
            raise DatabaseError(str(exc)) from exc

    async def count(self, **filters: Any) -> int:
        """Return count of matching records asynchronously.

        Args:
            **filters: Field-value filtering criteria.

        Returns:
            Total count of matching records.

        Raises:
            DatabaseError: If query execution fails.
        """
        try:
            stmt = select(func.count()).select_from(self._model_cls)
            for k, v in filters.items():
                if hasattr(self._model_cls, k):
                    stmt = stmt.where(getattr(self._model_cls, k) == v)
            result = await self._session.execute(stmt)
            return int(result.scalar_one())
        except Exception as exc:
            raise DatabaseError(str(exc)) from exc

    async def delete(self, entity_id: ID) -> bool:
        """Delete an entity by primary key asynchronously.

        Args:
            entity_id: Primary key identifier.

        Returns:
            True if entity was found and deleted, otherwise False.

        Raises:
            DatabaseError: If deletion fails.
        """
        try:
            entity = await self._session.get(self._model_cls, entity_id)
            if entity is None:
                return False
            await self._session.delete(entity)
            await self._session.flush()
            return True
        except Exception as exc:
            raise DatabaseError(str(exc)) from exc

    async def get(self, entity_id: ID) -> T | None:
        """Retrieve entity by primary key identifier asynchronously.

        Args:
            entity_id: Primary key identifier.

        Returns:
            Entity instance if found, otherwise None.

        Raises:
            DatabaseError: If query execution fails.
        """
        return await self.get_by_id(entity_id)

    async def get_by_id(self, entity_id: ID) -> T | None:
        """Retrieve entity by unique identifier asynchronously.

        Args:
            entity_id: Primary key identifier.

        Returns:
            Entity instance if found, otherwise None.

        Raises:
            DatabaseError: If query execution fails.
        """
        try:
            return await self._session.get(self._model_cls, entity_id)
        except Exception as exc:
            raise DatabaseError(str(exc)) from exc

    async def list(
        self, offset: int = 0, limit: int = 100, **filters: Any
    ) -> Sequence[T]:
        """Query a page of entities matching optional attribute filters asynchronously.

        Args:
            offset: Pagination offset index.
            limit: Maximum number of records to return.
            **filters: Field-value filtering criteria.

        Returns:
            Sequence of matching entities.

        Raises:
            DatabaseError: If query execution fails.
        """
        try:
            stmt = select(self._model_cls).offset(offset).limit(limit)
            for k, v in filters.items():
                if hasattr(self._model_cls, k):
                    stmt = stmt.where(getattr(self._model_cls, k) == v)
            result = await self._session.execute(stmt)
            return list(result.scalars().all())
        except Exception as exc:
            raise DatabaseError(str(exc)) from exc

    async def remove(self, entity_id: ID) -> None:
        """Remove an entity by unique identifier asynchronously.

        Args:
            entity_id: Primary key identifier.

        Returns:
            None.

        Raises:
            DatabaseError: If deletion fails.
        """
        await self.delete(entity_id)

    async def update(self, entity: T) -> T:
        """Update an existing entity in the session asynchronously.

        Args:
            entity: Modified entity instance.

        Returns:
            The merged entity instance.

        Raises:
            UniqueConstraintViolationError: If constraint violation occurs.
            DatabaseError: If update fails.
        """
        try:
            merged = await self._session.merge(entity)
            await self._session.flush()
            return merged
        except IntegrityError as exc:
            raise UniqueConstraintViolationError(str(exc.orig or exc)) from exc
        except Exception as exc:
            raise DatabaseError(str(exc)) from exc

    # Aliases satisfying AsyncRepositoryPort interface
    add_async = add
    get_by_id_async = get_by_id
    remove_async = remove


__all__ = [
    "AsyncSqlAlchemyRepository",
    "SqlAlchemyRepository",
]
