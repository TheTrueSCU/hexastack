"""Open Policy Agent (OPA) policy evaluation adapter.

Notes/Architectural Intent:
    Evaluates policy queries against OPA's HTTP Data API (v1/data/{policy_path}).
    Passes user identity, roles, permissions, tenant_id, action, resource, and extra context.
"""

from collections.abc import Mapping
from typing import Any

from hexastack_auth.domain.models import Identity
from hexastack_auth.ports.policy import AuthorizationPolicyPort
from hexastack_core.domain.exceptions import MissingDependencyError

__all__ = [
    "OpaPolicyAdapter",
]


class OpaPolicyAdapter(AuthorizationPolicyPort):
    """AuthorizationPolicyPort implementation querying Open Policy Agent (OPA)."""

    def __init__(
        self,
        base_url: str = "http://localhost:8181",
        default_policy_path: str = "v1/data/authz/allow",
        timeout: float = 3.0,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.default_policy_path = default_policy_path.strip("/")
        self.timeout = timeout

    def is_authorized(
        self,
        identity: Identity,
        action: str,
        resource: str,
        *,
        context: Mapping[str, Any] | None = None,
    ) -> bool:
        """Evaluate policy rule against OPA REST Data API."""
        try:
            import httpx
        except ImportError as e:
            raise MissingDependencyError(
                "httpx is required for OpaPolicyAdapter. "
                "Install with 'pip install hexastack-auth[opa]'."
            ) from e

        # Determine target policy path (use action if it starts with 'v1/data/' or 'policies/')
        policy_path = (
            action.strip("/")
            if action.startswith("v1/data/") or action.startswith("policies/")
            else self.default_policy_path
        )
        url = f"{self.base_url}/{policy_path}"

        input_payload = {
            "input": {
                "identity": {
                    "user_id": identity.user_id,
                    "tenant_id": identity.tenant_id,
                    "roles": list(identity.roles),
                    "permissions": list(identity.permissions),
                    "claims": dict(identity.claims),
                    "is_authenticated": identity.is_authenticated,
                },
                "action": action,
                "resource": resource,
                "context": dict(context or {}),
            }
        }

        try:
            with httpx.Client(timeout=self.timeout) as client:
                response = client.post(url, json=input_payload)
                if response.status_code != 200:
                    return False

                data = response.json()
                result = data.get("result")
                if isinstance(result, bool):
                    return result
                if isinstance(result, dict):
                    return bool(result.get("allow", False))
                return bool(result)
        except Exception:
            return False
