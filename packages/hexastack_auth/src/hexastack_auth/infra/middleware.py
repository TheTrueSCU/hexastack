import inspect
from collections.abc import Callable
from typing import Any, cast

from hexastack_auth.domain.exceptions import (
    InsufficientPermissionsError,
    InvalidCredentialsError,
)
from hexastack_auth.domain.models import AnonymousIdentity, Identity
from hexastack_auth.infra.decorators import AuthMetadata, get_auth_metadata
from hexastack_core.domain import Generic
from hexastack_core.utils.context import UserContext, get_user_context


class AuthorizationMiddleware:
    """CQRS middleware evaluating declarative @authorize rules on dispatched messages.

    Notes/Architectural Intent:
        Intercepts Command and Query execution before reaching handlers.
        Enforces security invariants centrally (RBAC, OPA, OpenFGA, SPIFFE)
        regardless of driving transport.
    """

    def __init__(
        self,
        enabled: bool = True,
        policy_adapter: Any | None = None,
    ) -> None:
        """Initialize authorization middleware.

        Args:
            enabled: Whether authorization checks are active.
            policy_adapter: Optional AuthorizationPolicyPort for OPA/OpenFGA evaluations.
        """
        self._enabled = enabled
        self._policy_adapter = policy_adapter

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
            InsufficientPermissionsError: If caller lacks roles, permissions, or policy grant.
        """
        if self._enabled:
            meta = get_auth_metadata(instance)
            if meta is not None:
                evaluate_authorization(
                    meta,
                    instance=instance,
                    policy_adapter=self._policy_adapter,
                )

        result = next_call(instance)
        if inspect.isawaitable(result):

            async def _async_wrap() -> Any:
                return await result

            return cast("R", _async_wrap())
        return result

    @property
    def enabled(self) -> bool:
        """Whether authorization checks are actively enforced."""
        return self._enabled


__all__ = [
    "AuthorizationMiddleware",
    "evaluate_authorization",
]


def _check_permissions(metadata: AuthMetadata, identity: Identity) -> None:
    """Verify permission requirements against effective identity."""
    if not metadata.permissions:
        return
    if metadata.match_all_permissions:
        if not identity.has_all_permissions(metadata.permissions):
            raise InsufficientPermissionsError(
                f"Identity '{identity.user_id}' lacks required permissions: {sorted(metadata.permissions)}"
            )
    elif not identity.has_any_permission(metadata.permissions):
        raise InsufficientPermissionsError(
            f"Identity '{identity.user_id}' lacks any of the required permissions: {sorted(metadata.permissions)}"
        )


def _check_roles(metadata: AuthMetadata, identity: Identity) -> None:
    """Verify role requirements against effective identity."""
    if not metadata.roles:
        return
    if metadata.match_all_roles:
        if not identity.has_all_roles(metadata.roles):
            raise InsufficientPermissionsError(
                f"Identity '{identity.user_id}' lacks required roles: {sorted(metadata.roles)}"
            )
    elif not identity.has_any_role(metadata.roles):
        raise InsufficientPermissionsError(
            f"Identity '{identity.user_id}' lacks any of the required roles: {sorted(metadata.roles)}"
        )


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
    claims = dict(getattr(identity, "claims", {}))
    is_auth = bool(getattr(identity, "is_authenticated", True))

    return Identity(
        user_id=str(user_id),
        roles=roles,
        permissions=permissions,
        claims=claims,
        tenant_id=str(tenant_id) if tenant_id is not None else None,
        is_authenticated=is_auth,
    )


def evaluate_authorization(
    metadata: AuthMetadata,
    identity: Any | None = None,
    *,
    instance: Any | None = None,
    policy_adapter: Any | None = None,
) -> None:
    """Evaluate AuthMetadata against the current or provided Identity.

    Args:
        metadata: AuthMetadata defining the security requirements.
        identity: Optional explicit Identity or UserContext.
        instance: Optional Command/Query message instance for contextual checks.
        policy_adapter: Optional AuthorizationPolicyPort for OPA/OpenFGA evaluation.

    Raises:
        InvalidCredentialsError: If caller is unauthenticated when required.
        InsufficientPermissionsError: If caller lacks required roles, permissions, or policy grant.
    """
    effective_id = _resolve_effective_identity(identity)

    # 1. Check Authentication requirement
    if metadata.require_authenticated and not effective_id.is_authenticated:
        raise InvalidCredentialsError("Authentication credentials are required.")

    # 2. Check SPIFFE workload identity restrictions
    if metadata.spiffe_ids:
        caller_spiffe = effective_id.claims.get("spiffe_id") or effective_id.claims.get(
            "sub"
        )
        if caller_spiffe not in metadata.spiffe_ids:
            raise InsufficientPermissionsError(
                f"Caller SPIFFE identity '{caller_spiffe}' is not authorized. Allowed: {metadata.spiffe_ids}"
            )

    # 3. Check Roles & Permissions
    _check_roles(metadata, effective_id)
    _check_permissions(metadata, effective_id)

    # 4. Check OPA Policy if specified
    if metadata.policy and policy_adapter is not None:
        action = metadata.policy
        resource = (
            getattr(instance, "__class__", type(instance)).__name__
            if instance
            else "default"
        )
        payload_ctx = dict(getattr(instance, "__dict__", {})) if instance else {}
        allowed = policy_adapter.is_authorized(
            identity=effective_id,
            action=action,
            resource=resource,
            context=payload_ctx,
        )
        if not allowed:
            raise InsufficientPermissionsError(
                f"Identity '{effective_id.user_id}' denied by policy '{metadata.policy}'"
            )

    # 5. Check OpenFGA ReBAC relation if specified
    if metadata.relation and policy_adapter is not None:
        relation = metadata.relation
        obj_id = "default"
        if instance and metadata.object_id_field:
            obj_id = str(getattr(instance, metadata.object_id_field, "default"))
        resource = f"{metadata.object_type or 'object'}:{obj_id}"
        allowed = policy_adapter.is_authorized(
            identity=effective_id,
            action=relation,
            resource=resource,
        )
        if not allowed:
            raise InsufficientPermissionsError(
                f"Identity '{effective_id.user_id}' lacks relation '{metadata.relation}' on '{resource}'"
            )
