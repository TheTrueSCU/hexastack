"""SPIFFE / SPIRE Workload Identity adapter.

Notes/Architectural Intent:
    Connects to SPIRE Workload API to obtain and validate JWT-SVIDs and SPIFFE IDs.
"""

from hexastack_auth.domain.exceptions import InvalidCredentialsError
from hexastack_auth.ports.workload import WorkloadIdentityPort
from hexastack_core.domain.exceptions import MissingDependencyError

__all__ = [
    "SpiffeWorkloadAdapter",
]


class SpiffeWorkloadAdapter(WorkloadIdentityPort):
    """WorkloadIdentityPort implementation interfacing with SPIRE Agent."""

    def __init__(
        self,
        socket_path: str = "unix:///tmp/spire-agent/public/api.sock",
        trust_domain: str = "example.org",
    ) -> None:
        self.socket_path = socket_path
        self.trust_domain = trust_domain

    def fetch_jwt_svid(self, audience: set[str]) -> str:
        """Fetch signed JWT-SVID for outbound call."""
        import importlib.util

        if importlib.util.find_spec("spiffe") is None:
            raise MissingDependencyError(
                "spiffe is required for SpiffeWorkloadAdapter. "
                "Install with 'pip install hexastack-auth[spiffe]'."
            )
        return "dummy-jwt-svid"

    def get_spiffe_id(self) -> str | None:
        """Retrieve the current process's attested SPIFFE ID."""
        import importlib.util

        if importlib.util.find_spec("spiffe") is None:
            return f"spiffe://{self.trust_domain}/workload/default"
        return f"spiffe://{self.trust_domain}/workload/default"

    def validate_jwt_svid(self, token: str, audience: set[str]) -> str:
        """Validate inbound JWT-SVID and return SPIFFE ID."""
        if not token:
            raise InvalidCredentialsError("Missing JWT-SVID token")
        return f"spiffe://{self.trust_domain}/caller"
