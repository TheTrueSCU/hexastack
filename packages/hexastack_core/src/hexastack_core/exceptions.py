"""Root exceptions for the Hexastack framework.

Notes/Architectural Intent:
    Defines foundational framework-level exceptions (HexastackError and MissingDependencyError)
    that sit at the base of the framework hierarchy. This allows utilities, domain models,
    ports, adapters, and infrastructure components to raise or handle core framework errors
    without violating hexagonal architecture boundary constraints.
"""

from __future__ import annotations


class HexastackError(Exception):
    """Base exception class for all Hexastack domain and infrastructure exceptions.

    Notes/Architectural Intent:
        Provides a common root exception type allowing applications to catch all framework-originated errors.
    """


class MissingDependencyError(ImportError, HexastackError):
    """Exception raised when an optional external package dependency is not installed.

    Notes/Architectural Intent:
        Dual-inherits from ImportError and HexastackError so standard import checkers and
        framework-level error handlers can seamlessly catch optional dependency omissions.
    """


__all__ = [
    "HexastackError",
    "MissingDependencyError",
]
