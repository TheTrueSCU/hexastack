import uuid
from collections.abc import Iterator
from contextlib import contextmanager
from contextvars import ContextVar, Token
from dataclasses import dataclass, field


@dataclass(frozen=True)
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


__all__ = [
    "correlation_id_ctx",
    "correlation_scope",
    "get_correlation_id",
    "get_user_context",
    "new_correlation_id",
    "set_correlation_id",
    "set_user_context",
    "user_ctx",
    "UserContext",
]


@contextmanager
def correlation_scope(cid: str | None = None) -> Iterator[str]:
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
    return correlation_id_ctx.get()


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
