"""OpenFGA Fine-Grained ReBAC policy evaluation adapter.

Notes/Architectural Intent:
    Evaluates relationship-based access control checks against OpenFGA.
    Maps user identity, relation, and object tuples (e.g., user:X can_edit document:Y).
"""

from collections.abc import Mapping
from typing import Any

from hexastack_auth.domain.models import Identity
from hexastack_auth.ports.policy import AuthorizationPolicyPort
from hexastack_core.domain.exceptions import MissingDependencyError

__all__ = [
    "OpenFgaPolicyAdapter",
]


class OpenFgaPolicyAdapter(AuthorizationPolicyPort):
    """AuthorizationPolicyPort implementation querying OpenFGA."""

    def __init__(
        self,
        api_url: str = "http://localhost:8080",
        store_id: str = "",
        model_id: str | None = None,
    ) -> None:
        self.api_url = api_url.rstrip("/")
        self.store_id = store_id
        self.model_id = model_id

    def is_authorized(
        self,
        identity: Identity,
        action: str,
        resource: str,
        *,
        context: Mapping[str, Any] | None = None,
    ) -> bool:
        """Evaluate relationship check via OpenFGA Check API."""
        try:
            import httpx
        except ImportError as e:
            raise MissingDependencyError(
                "httpx is required for OpenFgaPolicyAdapter. "
                "Install with 'pip install hexastack-auth[openfga]'."
            ) from e

        user = f"user:{identity.user_id}" if identity.user_id else "user:anonymous"
        relation = action
        obj = resource if ":" in resource else f"object:{resource}"

        url = f"{self.api_url}/stores/{self.store_id}/check"
        payload = {
            "tuple_key": {
                "user": user,
                "relation": relation,
                "object": obj,
            }
        }
        if self.model_id:
            payload["authorization_model_id"] = self.model_id

        try:
            with httpx.Client(timeout=3.0) as client:
                response = client.post(url, json=payload)
                if response.status_code != 200:
                    return False
                return bool(response.json().get("allowed", False))
        except Exception:
            return False
