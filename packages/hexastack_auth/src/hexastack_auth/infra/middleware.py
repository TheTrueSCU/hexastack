import inspect
from collections.abc import Callable
from typing import Any, cast

from hexastack_core.domain import Generic
from hexastack_core.utils.context import UserContext, get_user_context

from hexastack_auth.domain.exceptions import (
    InsufficientPermissionsError,
    InvalidCredentialsError,
)
from hexastack_auth.domain.models import AnonymousIdentity, Identity
from hexastack_auth.infra.decorators import AuthMetadata, get_auth_metadata


def _resolve_effective_identity(identity: Any | None) -> Identity:
    """Normalize UserContext or Identity into an Identity instance."""
    if identity is None:
        raw_ctx = get_user_context()
        if raw_ctx is None:
            return AnonymousIdentity()
        identity = raw_ctx

    if isinstance(identity, Identity):
        return identity

    if isinstance(identity, UserContext):
        return Identity(
            user_id=identity.user_id,
            roles=frozenset(identity.roles),
            permissions=frozenset(),
            tenant_id=identity.tenant_id,
            is_authenticated=True,
        )

    # Fallback for duck-typed objects
    user_id = getattr(identity, "user_id", "unknown")
    roles = frozenset(getattr(identity, "roles", []))
    permissions = frozenset(getattr(identity, "permissions", []))
    tenant_id = getattr(identity, "tenant_id", None)
    is_auth = bool(getattr(identity, "is_authenticated", True))

    return Identity(
        user_id=str(user_id),
        roles=roles,
        permissions=permissions,
        tenant_id=str(tenant_id) if tenant_id is not None else None,
        is_authenticated=is_auth,
    )


def evaluate_authorization(
    metadata: AuthMetadata,
    identity: Any | None = None,
) -> None:
    """Evaluate AuthMetadata against the current or provided Identity.

    Args:
        metadata: AuthMetadata defining the security requirements.
        identity: Optional explicit Identity or UserContext.

    Raises:
        InvalidCredentialsError: If caller is unauthenticated when required.
        InsufficientPermissionsError: If caller lacks required roles or permissions.
    """
    effective_id = _resolve_effective_identity(identity)

    # 1. Check Authentication requirement
    if metadata.require_authenticated and not effective_id.is_authenticated:
        raise InvalidCredentialsError("Authentication credentials are required.")

    # 2. Check Roles
    if metadata.roles:
        if metadata.match_all_roles:
            if not effective_id.has_all_roles(metadata.roles):
                raise InsufficientPermissionsError(
                    f"Identity '{effective_id.user_id}' lacks required roles: {sorted(metadata.roles)}"
                )
        else:
            if not effective_id.has_any_role(metadata.roles):
                raise InsufficientPermissionsError(
                    f"Identity '{effective_id.user_id}' lacks any of the required roles: {sorted(metadata.roles)}"
                )

    # 3. Check Permissions
    if metadata.permissions:
        if metadata.match_all_permissions:
            if not effective_id.has_all_permissions(metadata.permissions):
                raise InsufficientPermissionsError(
                    f"Identity '{effective_id.user_id}' lacks required permissions: {sorted(metadata.permissions)}"
                )
        else:
            if not effective_id.has_any_permission(metadata.permissions):
                raise InsufficientPermissionsError(
                    f"Identity '{effective_id.user_id}' lacks any of the required permissions: {sorted(metadata.permissions)}"
                )


class AuthorizationMiddleware:
    """CQRS middleware evaluating declarative @authorize rules on dispatched messages.

    Notes/Architectural Intent:
        Intercepts Command and Query execution before reaching handlers.
        Enforces security invariants centrally regardless of driving transport.
    """

    def __init__(self, enabled: bool = True) -> None:
        """Initialize authorization middleware.

        Args:
            enabled: Whether authorization checks are active.
        """
        self._enabled = enabled

    def __call__[G: Generic, R](
        self,
        instance: G,
        next_call: Callable[[G], R],
    ) -> R:
        """Execute authorization evaluation before dispatching to the next handler.

        Args:
            instance: The command or query message instance.
            next_call: The downstream handler or next middleware in chain.

        Returns:
            The handler return value.

        Raises:
            InvalidCredentialsError: If caller is not authenticated.
            InsufficientPermissionsError: If caller lacks roles or permissions.
        """
        if self._enabled:
            meta = get_auth_metadata(instance)
            if meta is not None:
                evaluate_authorization(meta)

        result = next_call(instance)
        if inspect.isawaitable(result):

            async def _async_wrap() -> Any:
                return await result

            return cast(R, _async_wrap())
        return result


__all__ = [
    "AuthorizationMiddleware",
    "evaluate_authorization",
]
