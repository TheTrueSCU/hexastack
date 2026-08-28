from abc import ABC, abstractmethod
from datetime import timedelta

from hexastack_auth.domain.models import Identity


class SecurityPort(ABC):
    """Abstract port interface defining token generation, verification, and authentication operations.

    Notes/Architectural Intent:
        Decouples security token issuing and verification from concrete cryptographic
        standards (JWT, Paseto, OAuth2 introspect), enabling seamless integration across
        in-memory testing, PyJWT, or external identity providers.
    """

    @abstractmethod
    def create_token(
        self,
        identity: Identity,
        *,
        ttl: timedelta | int | None = None,
    ) -> str:
        """Issue a signed security token encoding the supplied identity.

        Args:
            identity: The authenticated Identity domain object.
            ttl: Optional time-to-live as a timedelta or duration in seconds.

        Returns:
            Cryptographically signed token string.

        Raises:
            AuthError: If token generation or signing fails.
        """
        pass

    @abstractmethod
    def verify_token(self, token: str) -> Identity:
        """Decode, validate signature, and reconstruct an Identity from a security token.

        Args:
            token: The raw signed security token string.

        Returns:
            Verified Identity domain object.

        Raises:
            InvalidTokenError: If token format or cryptographic signature is invalid.
            TokenExpiredError: If token has expired past its expiration timestamp.
            AuthError: If general verification fails.
        """
        pass


__all__ = [
    "SecurityPort",
]
