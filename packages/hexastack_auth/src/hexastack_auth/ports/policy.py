"""Abstract policy evaluation port interface for OPA and OpenFGA.

Notes/Architectural Intent:
    Decouples declarative @authorize policies and fine-grained relationship
    checks (ReBAC / ABAC) from concrete policy engine SDKs.
"""

from collections.abc import Mapping
from typing import Any, Protocol, runtime_checkable

from hexastack_auth.domain.models import Identity

__all__ = [
    "AuthorizationPolicyPort",
]


@runtime_checkable
class AuthorizationPolicyPort(Protocol):
    """Port interface for externalized policy engines (OPA, OpenFGA)."""

    def is_authorized(
        self,
        identity: Identity,
        action: str,
        resource: str,
        *,
        context: Mapping[str, Any] | None = None,
    ) -> bool:
        """Evaluate whether an identity is authorized to perform action on resource.

        Args:
            identity: The active authenticated Identity domain model.
            action: Action being performed (e.g. 'can_edit', 'orders:cancel', or policy rule name).
            resource: Target resource or object identifier (e.g. 'doc:123', 'finance.invoices').
            context: Optional contextual parameters (request attributes, payload fields, tenant info).

        Returns:
            True if authorized, False otherwise.
        """
