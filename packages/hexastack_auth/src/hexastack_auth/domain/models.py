from collections.abc import Collection
from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class Identity:
    """Immutable domain representation of an authenticated security principal.

    Notes/Architectural Intent:
        Encapsulates the caller's verified subject identifier, role memberships,
        granular permissions, optional multi-tenant partition, and raw JWT claims.
        Frozen to guarantee thread/async safety across task boundaries.
    """

    user_id: str
    roles: frozenset[str] = field(default_factory=frozenset)
    permissions: frozenset[str] = field(default_factory=frozenset)
    tenant_id: str | None = None
    claims: dict[str, Any] = field(default_factory=dict)
    is_authenticated: bool = True

    def has_role(self, role: str) -> bool:
        """Check if the identity holds a specific role.

        Args:
            role: The role name to verify.

        Returns:
            True if the role is present in this identity's roles.
        """
        return role in self.roles

    def has_permission(self, permission: str) -> bool:
        """Check if the identity holds a specific permission.

        Args:
            permission: The permission string to verify.

        Returns:
            True if the permission is present in this identity's permissions.
        """
        return permission in self.permissions

    def has_all_roles(self, roles: Collection[str]) -> bool:
        """Check if the identity holds every role in the given collection.

        Args:
            roles: Collection of required role strings.

        Returns:
            True if all required roles are held.
        """
        return set(roles).issubset(self.roles)

    def has_any_role(self, roles: Collection[str]) -> bool:
        """Check if the identity holds at least one role in the given collection.

        Args:
            roles: Collection of role strings.

        Returns:
            True if at least one role is held.
        """
        return bool(set(roles).intersection(self.roles))

    def has_all_permissions(self, permissions: Collection[str]) -> bool:
        """Check if the identity holds every permission in the given collection.

        Args:
            permissions: Collection of required permission strings.

        Returns:
            True if all required permissions are held.
        """
        return set(permissions).issubset(self.permissions)

    def has_any_permission(self, permissions: Collection[str]) -> bool:
        """Check if the identity holds at least one permission in the given collection.

        Args:
            permissions: Collection of permission strings.

        Returns:
            True if at least one permission is held.
        """
        return bool(set(permissions).intersection(self.permissions))


@dataclass(frozen=True)
class AnonymousIdentity(Identity):
    """Domain representation of an unauthenticated or anonymous caller.

    Notes/Architectural Intent:
        Null Object pattern providing a safe default identity when no credentials
        are supplied, avoiding None checks across security checks.
    """

    user_id: str = "anonymous"
    roles: frozenset[str] = field(default_factory=frozenset)
    permissions: frozenset[str] = field(default_factory=frozenset)
    tenant_id: str | None = None
    claims: dict[str, Any] = field(default_factory=dict)
    is_authenticated: bool = False


@dataclass(frozen=True)
class TokenPayload:
    """Parsed token payload representation.

    Notes/Architectural Intent:
        Standardized representation of decoded token claims before conversion
        into an active Identity.
    """

    subject: str
    roles: list[str] = field(default_factory=list)
    permissions: list[str] = field(default_factory=list)
    tenant_id: str | None = None
    issued_at: int | None = None
    expires_at: int | None = None
    custom_claims: dict[str, Any] = field(default_factory=dict)


__all__ = [
    "AnonymousIdentity",
    "Identity",
    "TokenPayload",
]
