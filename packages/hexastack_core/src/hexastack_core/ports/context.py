"""Abstract context ports and ambient variable protocols.

Notes/Architectural Intent:
    Defines the contract for ambient context storage (such as correlation IDs,
    multi-tenant boundaries, and security credentials) across synchronous and
    asynchronous task contexts. Adheres to PEP 567 semantics while supporting
    pure-Python fallbacks on edge and microcontroller runtimes lacking `contextvars`.
"""

from __future__ import annotations

from typing import Any, Protocol, TypeVar, runtime_checkable

T = TypeVar("T")


@runtime_checkable
class TokenPort[T](Protocol):
    """Protocol representing the prior state of a context variable before mutation.

    Notes/Architectural Intent:
        Standardizes the reset token returned by context variable mutation operations.
    """

    @property
    def old_value(self) -> T | None:
        """Prior value held by the context variable."""
        ...


@runtime_checkable
class ContextVarPort[T](Protocol):
    """Protocol for ambient context variables across async task contexts.

    Notes/Architectural Intent:
        Enables seamless switching between standard library `contextvars.ContextVar`
        and lightweight edge implementations without coupling to standard library C-extensions.
    """

    @property
    def name(self) -> str:
        """Name of the context variable."""
        ...

    def get(self, default: T | None = None) -> T | None:
        """Retrieve the current value of the context variable."""
        ...

    def set(self, value: T) -> Any:
        """Set a new value for the context variable and return a reset token."""
        ...

    def reset(self, token: Any) -> None:
        """Reset the context variable to its state prior to the corresponding set call."""
        ...


__all__ = [
    "ContextVarPort",
    "TokenPort",
]
