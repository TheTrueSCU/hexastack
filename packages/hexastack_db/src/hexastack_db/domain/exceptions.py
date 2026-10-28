from typing import Any

from hexastack_core.domain.exceptions import HexastackError


class DatabaseError(HexastackError):
    """Base exception for database and persistence errors in Hexastack.

    Notes/Architectural Intent:
        Serves as the root domain exception for repository and UnitOfWork operations.
    """


class DatabaseConnectionError(DatabaseError):
    """Exception raised when failing to connect to the database engine.

    Notes/Architectural Intent:
        Identifies network or configuration issues when initializing database connections.
    """


class ColumnarQueryError(DatabaseError):
    """Exception raised during zero-copy columnar projection or export execution.

    Notes/Architectural Intent:
        Wraps low-level Polars, PyArrow, or database cursor extraction failures
        into domain persistence errors.
    """

    def __init__(self, message: str, query: str | None = None) -> None:
        """Initialize ColumnarQueryError with optional query string.

        Args:
            message: Error description.
            query: Optional SQL query string that caused the failure.
        """
        self.query = query
        suffix = f" [query={query}]" if query else ""
        super().__init__(f"{message}{suffix}")


class EntityNotFoundError(DatabaseError):
    """Exception raised when a requested database entity cannot be found by ID or filter.

    Notes/Architectural Intent:
        Provides clear diagnostic messaging when looking up nonexistent records.
    """

    def __init__(self, entity_cls: type[Any], entity_id: Any) -> None:
        """Initialize exception with entity type and missing ID.

        Args:
            entity_cls: The entity model class.
            entity_id: The identifier that was searched for.
        """
        self.entity_cls = entity_cls
        self.entity_id = entity_id
        super().__init__(
            f"Entity '{entity_cls.__name__}' with id '{entity_id}' was not found."
        )


class UniqueConstraintViolationError(DatabaseError):
    """Exception raised when an insert or update violates a unique database constraint.

    Notes/Architectural Intent:
        Translates raw database integrity errors into domain-level constraint exceptions.
    """

    def __init__(self, message: str = "Unique constraint violation occurred.") -> None:
        """Initialize with error message.

        Args:
            message: Descriptive constraint error message.
        """
        super().__init__(message)


__all__ = [
    "ColumnarQueryError",
    "DatabaseConnectionError",
    "DatabaseError",
    "EntityNotFoundError",
    "UniqueConstraintViolationError",
]
