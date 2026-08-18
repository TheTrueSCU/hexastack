from collections.abc import Callable, Sequence
from dataclasses import dataclass
from typing import Any

_AUTH_METADATA_ATTR = "__hexastack_auth__"


@dataclass(frozen=True)
class AuthMetadata:
    """Metadata describing required authentication and authorization rules for a target.

    Notes/Architectural Intent:
        Attached to Command/Query models or handlers via decorators and inspected
        by AuthorizationMiddleware or transport adapters (FastAPI, gRPC, GraphQL).
    """

    roles: tuple[str, ...] = ()
    permissions: tuple[str, ...] = ()
    require_authenticated: bool = True
    match_all_roles: bool = True
    match_all_permissions: bool = True


__all__ = [
    "AuthMetadata",
    "authenticated",
    "authorize",
    "get_auth_metadata",
    "requires_permission",
    "requires_role",
]


def authenticated[T: Any]() -> Callable[[T], T]:
    """Convenience decorator requiring an authenticated caller without specific roles.

    Returns:
        Decorated target with require_authenticated=True.
    """
    return authorize(require_authenticated=True)


def authorize[T: Any](
    *,
    roles: Sequence[str] = (),
    permissions: Sequence[str] = (),
    require_authenticated: bool = True,
    match_all_roles: bool = True,
    match_all_permissions: bool = True,
) -> Callable[[T], T]:
    """Decorator marking a Command, Query, or Handler with authorization requirements.

    Notes/Architectural Intent:
        Enforces declarative Role-Based Access Control (RBAC) and granular permission
        policies across any execution channel (REST, GraphQL, gRPC, CLI, MCP).

    Args:
        roles: Sequence of required role names.
        permissions: Sequence of required permission strings.
        require_authenticated: Whether caller must be authenticated (default True).
        match_all_roles: If True, requires all roles; if False, requires at least one.
        match_all_permissions: If True, requires all permissions; if False, requires at least one.

    Returns:
        Decorated class or function with attached AuthMetadata.
    """

    def decorator(target: T) -> T:
        meta = AuthMetadata(
            roles=tuple(roles),
            permissions=tuple(permissions),
            require_authenticated=require_authenticated,
            match_all_roles=match_all_roles,
            match_all_permissions=match_all_permissions,
        )
        setattr(target, _AUTH_METADATA_ATTR, meta)
        return target

    return decorator


def get_auth_metadata(target: Any) -> AuthMetadata | None:
    """Retrieve attached AuthMetadata from a class, instance, or function.

    Args:
        target: Object, class, or callable to inspect.

    Returns:
        AuthMetadata if present, None otherwise.
    """
    if target is None:
        return None
    # Check directly on target, or on target's class if instance
    if hasattr(target, _AUTH_METADATA_ATTR):
        return getattr(target, _AUTH_METADATA_ATTR)  # type: ignore[no-any-return]
    if hasattr(type(target), _AUTH_METADATA_ATTR):
        return getattr(type(target), _AUTH_METADATA_ATTR)  # type: ignore[no-any-return]
    return None


def requires_permission[T: Any](*permissions: str) -> Callable[[T], T]:
    """Convenience decorator requiring the caller to possess specified permissions.

    Args:
        *permissions: One or more required permission strings.

    Returns:
        Decorated target with specified permissions.
    """
    return authorize(permissions=permissions, require_authenticated=True)


def requires_role[T: Any](*roles: str) -> Callable[[T], T]:
    """Convenience decorator requiring the caller to possess specified roles.

    Args:
        *roles: One or more required role strings.

    Returns:
        Decorated target with specified roles.
    """
    return authorize(roles=roles, require_authenticated=True)
