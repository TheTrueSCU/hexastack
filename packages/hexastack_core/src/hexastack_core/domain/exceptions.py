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


__all__ = [
    "DependencyResolutionError",
    "HexastackError",
    "HexastackRegistryError",
    "MissingDependencyError",
    "UnitOfWorkError",
]
