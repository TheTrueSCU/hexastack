class HexastackError(Exception):
    """Base exception class for all Hexastack domain and infrastructure exceptions.

    Notes/Architectural Intent:
        Provides a common root exception type allowing applications to catch all framework-originated errors.
    """


class DependencyResolutionError(HexastackError):
    """Exception raised when a required dependency or container service cannot be resolved.

    Notes/Architectural Intent:
        Provides a standardized framework exception for missing DI bindings or application state.
    """


class HexastackRegistryError(HexastackError):
    """Exception raised when registry lookup or registration failures occur.

    Notes/Architectural Intent:
        Base exception for all registry-related errors across Hexastack packages.
    """


class MissingDependencyError(ImportError, HexastackError):
    """Exception raised when an optional external package dependency is not installed.

    Notes/Architectural Intent:
        Dual-inherits from ImportError and HexastackError so standard import checkers and
        framework-level error handlers can seamlessly catch optional dependency omissions.
    """


class UnitOfWorkError(HexastackError):
    """Exception raised when a Unit of Work transaction fails during execution.

    Notes/Architectural Intent:
        Raised by UnitOfWorkPort when reraise=True is set and an exception occurs
        within the context manager boundary, wrapping the original cause.
    """


class NotFoundError(HexastackError):
    """Domain exception raised when a requested entity or aggregate is not found."""


class ValidationError(HexastackError):
    """Domain exception raised when business validation or invariant checking fails."""


class ConflictError(HexastackError):
    """Domain exception raised when a resource state conflict occurs (e.g. duplicate key)."""


class AuthenticationError(HexastackError):
    """Domain exception raised when authentication credentials are missing or invalid."""


class PermissionDeniedError(HexastackError):
    """Domain exception raised when an authenticated caller lacks required authorization."""


class LockError(HexastackError):
    """Domain exception raised when a distributed lock operation fails."""


class LeaderElectionError(HexastackError):
    """Domain exception raised when leader election coordination fails."""


class StorageError(HexastackError):
    """Domain exception raised when an object or file storage operation fails."""


class StorageNotFoundError(StorageError, NotFoundError):
    """Domain exception raised when a requested storage object or path does not exist."""


__all__ = [
    "AuthenticationError",
    "ConflictError",
    "DependencyResolutionError",
    "HexastackError",
    "HexastackRegistryError",
    "LeaderElectionError",
    "LockError",
    "MissingDependencyError",
    "NotFoundError",
    "PermissionDeniedError",
    "StorageError",
    "StorageNotFoundError",
    "UnitOfWorkError",
    "ValidationError",
]
