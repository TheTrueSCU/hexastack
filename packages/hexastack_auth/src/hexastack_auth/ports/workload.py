"""Abstract Workload Identity port interface for SPIFFE / SPIRE.

Notes/Architectural Intent:
    Provides zero-trust microservice attestation, X.509 SVID mTLS credentials,
    and JWT-SVID issuance conforming to the CNCF SPIFFE specification.
"""

from typing import Protocol, runtime_checkable

__all__ = [
    "WorkloadIdentityPort",
]


@runtime_checkable
class WorkloadIdentityPort(Protocol):
    """Port interface for SPIFFE Workload API and SPIRE agent integration."""

    def get_spiffe_id(self) -> str | None:
        """Retrieve the local attested SPIFFE ID (e.g. 'spiffe://example.org/ns/prod/sa/order-service')."""
        ...

    def fetch_jwt_svid(self, audience: set[str]) -> str:
        """Fetch a signed JWT-SVID for outbound service-to-service calls.

        Args:
            audience: Target service audience identifiers.

        Returns:
            Cryptographically signed JWT-SVID token string.
        """
        ...

    def validate_jwt_svid(self, token: str, audience: set[str]) -> str:
        """Validate an inbound JWT-SVID token and return the verified SPIFFE ID.

        Args:
            token: The raw JWT-SVID token string.
            audience: Expected audience set.

        Returns:
            Verified caller SPIFFE ID string.
        """
        ...
