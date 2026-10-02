import secrets
import time
from datetime import timedelta

from hexastack_auth.domain.exceptions import (
    InvalidTokenError,
    TokenExpiredError,
)
from hexastack_auth.domain.models import Identity
from hexastack_auth.ports.password import PasswordHasherPort
from hexastack_auth.ports.security import SecurityPort


class InMemorySecurityService(SecurityPort):
    """In-memory security service implementation for fast, isolated testing.

    Notes/Architectural Intent:
        Stores issued tokens in a local dictionary with expiration timestamps.
        Eliminates cryptographic overhead in unit and property tests.
    """

    def __init__(self, default_ttl_seconds: int = 3600) -> None:
        """Initialize in-memory token store."""
        self._default_ttl_seconds = default_ttl_seconds
        self._tokens: dict[str, tuple[Identity, float | None]] = {}

    def clear(self) -> None:
        """Clear all stored tokens."""
        self._tokens.clear()

    def create_token(
        self,
        identity: Identity,
        *,
        ttl: timedelta | int | None = None,
    ) -> str:
        """Store identity and return a unique token key.

        Args:
            identity: Identity to associate with token.
            ttl: Optional TTL duration or seconds.

        Returns:
            Opaque token string.
        """
        token = f"mem_token_{secrets.token_urlsafe(24)}"
        if ttl is None:
            ttl_secs = self._default_ttl_seconds
        elif isinstance(ttl, timedelta):
            ttl_secs = int(ttl.total_seconds())
        else:
            ttl_secs = ttl

        exp_time = time.time() + ttl_secs if ttl_secs is not None else None
        self._tokens[token] = (identity, exp_time)
        return token

    def verify_token(self, token: str) -> Identity:
        """Look up identity by token key and check expiration.

        Args:
            token: Opaque token string.

        Returns:
            Associated Identity.

        Raises:
            InvalidTokenError: If token does not exist.
            TokenExpiredError: If token has expired.
        """
        if not token or token not in self._tokens:
            raise InvalidTokenError(f"Token '{token}' not recognized.")

        identity, exp_time = self._tokens[token]
        if exp_time is not None and time.time() > exp_time:
            del self._tokens[token]
            raise TokenExpiredError("In-memory token has expired.")

        return identity


class InMemoryPasswordHasher(PasswordHasherPort):
    """In-memory password hasher for rapid unit testing without key derivation delay.

    Notes/Architectural Intent:
        Prefixes plain password with 'mock_hash:' for instantaneous test execution.
    """

    def hash_password(self, plain_password: str) -> str:
        """Return a mock hashed password string."""
        return f"mock_hash:{plain_password}"

    def verify_password(self, plain_password: str, hashed_password: str) -> bool:
        """Verify plain password matches mock hash."""
        return hashed_password == f"mock_hash:{plain_password}"


__all__ = [
    "InMemoryPasswordHasher",
    "InMemorySecurityService",
]
