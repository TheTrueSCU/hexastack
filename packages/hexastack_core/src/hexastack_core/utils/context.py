"""Universal context propagation utilities for distributed tracing, correlation, and multi-tenancy.

Notes/Architectural Intent:
    Provides ambient context propagation using `ContextVarPort` and `TokenPort`.
    Delegates to standard library `contextvars` when available, and seamlessly
    falls back to pure-Python in-memory variable storage on MicroPython, edge runtimes,
    and single-threaded WebAssembly environments lacking PEP 567 support.
"""

from __future__ import annotations

import uuid
from collections.abc import Generator
from contextlib import contextmanager
from dataclasses import dataclass, field
from typing import Any, TypeVar

T = TypeVar("T")


class Token[T]:
    """Token representing the prior state of a context variable.

    Notes/Architectural Intent:
        Wraps either a native PEP 567 `contextvars.Token` or holds the prior state
        for pure-Python minimal runtime execution. Conforms to TokenPort.
    """

    def __init__(self, old_value: T | None, raw_token: Any = None) -> None:
        self._old_value = old_value
        self._raw_token = raw_token

    @property
    def old_value(self) -> T | None:
        """Prior value held by the context variable."""
        return self._old_value

    @property
    def raw_token(self) -> Any:
        """Underlying native token if running on standard contextvars."""
        return self._raw_token


class ContextVar[T]:
    """Universal ambient context variable adapter ensuring cross-runtime compatibility.

    Notes/Architectural Intent:
        Delegates to stdlib `contextvars.ContextVar` when available, falling back
        to in-memory pure Python storage on MicroPython or restricted WASM runtimes.
        Conforms to `ContextVarPort[T]`.
    """

    def __init__(self, name: str, *, default: T | None = None) -> None:
        self._name = name
        self._default = default
        self._impl: Any = None
        self._value: T | None = default
        try:
            import contextvars

            self._impl = contextvars.ContextVar(name, default=default)
        except (ImportError, AttributeError):
            self._impl = None

    @property
    def name(self) -> str:
        """Name of the context variable."""
        return self._name

    def get(self, default: T | None = None) -> T | None:
        """Retrieve the current value of the context variable."""
        if self._impl is not None:
            return self._impl.get() if default is None else self._impl.get(default)
        if self._value is not None:
            return self._value
        return self._default if default is None else default

    def set(self, value: T) -> Token[T]:
        """Set a new value and return a reset token."""
        if self._impl is not None:
            raw = self._impl.set(value)
            return Token(old_value=None, raw_token=raw)
        old = self._value
        self._value = value
        return Token(old_value=old)

    def reset(self, token: Token[T] | Any) -> None:
        """Reset the context variable to its state prior to the corresponding set call."""
        if self._impl is not None:
            raw = getattr(token, "raw_token", token)
            self._impl.reset(raw)
        else:
            old = getattr(token, "old_value", self._default)
            self._value = old


def create_context_var[T](name: str, *, default: T | None = None) -> ContextVar[T]:
    """Construct a universal context variable conforming to ContextVarPort.

    Args:
        name: Context variable name.
        default: Optional default value.

    Returns:
        Configured ContextVar instance.
    """
    return ContextVar(name, default=default)


@dataclass(frozen=True, slots=True)
class UserContext:
    """Dataclass encapsulating authenticated user and multi-tenancy context.

    Notes/Architectural Intent:
        Carries immutable security and tenant metadata across async task boundaries via ContextVar.
    """

    user_id: str
    roles: list[str] = field(default_factory=list)
    tenant_id: str | None = None


correlation_id_ctx: ContextVar[str] = ContextVar("correlation_id", default="")
user_ctx: ContextVar[UserContext | None] = ContextVar("user", default=None)


@contextmanager
def correlation_scope(cid: str | None = None) -> Generator[str]:
    """Execute a code block within a managed correlation ID scope.

    Notes/Architectural Intent:
        Guarantees that correlation_id_ctx is updated with either the given ID or
        a newly generated UUID4, and reliably resets back to the prior token on exit.

    Args:
        cid: Optional correlation ID string. If omitted, generates a fresh UUID4.

    Yields:
        The effective correlation ID string.
    """
    effective_cid = cid or str(uuid.uuid4())
    token = correlation_id_ctx.set(effective_cid)
    try:
        yield effective_cid
    finally:
        correlation_id_ctx.reset(token)


def get_correlation_id() -> str:
    """Retrieve the current correlation ID string from context.

    Returns:
        The active correlation ID, or an empty string if unset.
    """
    return correlation_id_ctx.get() or ""


def get_user_context() -> UserContext | None:
    """Retrieve the current UserContext instance from context.

    Returns:
        The active UserContext instance, or None if unauthenticated.
    """
    return user_ctx.get()


def new_correlation_id() -> str:
    """Generate, set, and return a new UUID4 correlation ID in the current context.

    Returns:
        Newly generated correlation ID string.
    """
    cid = str(uuid.uuid4())
    correlation_id_ctx.set(cid)
    return cid


def set_correlation_id(correlation_id: str) -> Token[str]:
    """Set the correlation ID for the current context.

    Args:
        correlation_id: The correlation ID string to set.

    Returns:
        Token object that can be used to reset the context variable.
    """
    return correlation_id_ctx.set(correlation_id)


def set_user_context(user: UserContext | None) -> Token[UserContext | None]:
    """Set the UserContext for the current context.

    Args:
        user: The UserContext instance to set, or None to clear.

    Returns:
        Token object that can be used to reset the context variable.
    """
    return user_ctx.set(user)


__all__ = [
    "ContextVar",
    "correlation_id_ctx",
    "correlation_scope",
    "create_context_var",
    "get_correlation_id",
    "get_user_context",
    "new_correlation_id",
    "set_correlation_id",
    "set_user_context",
    "Token",
    "user_ctx",
    "UserContext",
]
