from datetime import UTC, datetime, timedelta
from typing import Any

import jwt

from hexastack_auth.domain.exceptions import (
    AuthError,
    InvalidTokenError,
    TokenExpiredError,
)
from hexastack_auth.domain.models import Identity
from hexastack_auth.ports.security import SecurityPort


class JwtSecurityAdapter(SecurityPort):
    """Concrete token security adapter implementing SecurityPort using PyJWT.

    Notes/Architectural Intent:
        Implements industry-standard JSON Web Token encoding and cryptographic signature
        validation. Maps PyJWT exception hierarchies into clean Hexastack domain errors.
    """

    def __init__(
        self,
        secret_key: str,
        *,
        algorithm: str = "HS256",
        default_ttl_seconds: int = 3600,
        issuer: str | None = None,
        audience: str | None = None,
    ) -> None:
        """Initialize JWT security adapter.

        Args:
            secret_key: Secret key or private key for signing tokens.
            algorithm: Cryptographic algorithm (default 'HS256').
            default_ttl_seconds: Default expiration lifespan in seconds (default 3600).
            issuer: Optional expected token issuer string ('iss').
            audience: Optional expected token audience string ('aud').
        """
        self._secret_key = secret_key
        self._algorithm = algorithm
        self._default_ttl = timedelta(seconds=default_ttl_seconds)
        self._issuer = issuer
        self._audience = audience

    def create_token(
        self,
        identity: Identity,
        *,
        ttl: timedelta | int | None = None,
    ) -> str:
        """Issue a signed JWT token for the given identity.

        Args:
            identity: Identity to encode into claims.
            ttl: Optional TTL duration or seconds override.

        Returns:
            Signed JWT string.

        Raises:
            AuthError: If encoding fails.
        """
        now = datetime.now(UTC)
        if ttl is None:
            effective_ttl = self._default_ttl
        elif isinstance(ttl, int):
            effective_ttl = timedelta(seconds=ttl)
        else:
            effective_ttl = ttl

        exp = now + effective_ttl
        payload: dict[str, Any] = {
            "sub": identity.user_id,
            "roles": sorted(identity.roles),
            "permissions": sorted(identity.permissions),
            "iat": int(now.timestamp()),
            "exp": int(exp.timestamp()),
        }

        if identity.tenant_id is not None:
            payload["tenant_id"] = identity.tenant_id

        if self._issuer is not None:
            payload["iss"] = self._issuer

        if self._audience is not None:
            payload["aud"] = self._audience

        # Merge custom claims without overwriting standard registered claims
        for k, v in identity.claims.items():
            if k not in payload:
                payload[k] = v

        try:
            return jwt.encode(payload, self._secret_key, algorithm=self._algorithm)
        except Exception as exc:
            raise AuthError(f"JWT signing failed: {exc}") from exc

    def verify_token(self, token: str) -> Identity:
        """Decode and verify a JWT token, reconstructing the Identity.

        Args:
            token: The raw JWT string.

        Returns:
            Verified Identity domain instance.

        Raises:
            TokenExpiredError: If the token has expired.
            InvalidTokenError: If the signature or structure is invalid.
            AuthError: If general verification fails.
        """
        if not token:
            raise InvalidTokenError("Token string cannot be empty.")

        options = {"verify_exp": True}
        kwargs: dict[str, Any] = {
            "key": self._secret_key,
            "algorithms": [self._algorithm],
            "options": options,
        }

        if self._issuer is not None:
            kwargs["issuer"] = self._issuer
        if self._audience is not None:
            kwargs["audience"] = self._audience

        try:
            claims: dict[str, Any] = jwt.decode(token, **kwargs)
        except jwt.ExpiredSignatureError as exc:
            raise TokenExpiredError(f"JWT token expired: {exc}") from exc
        except jwt.PyJWTError as exc:
            raise InvalidTokenError(f"Invalid JWT token: {exc}") from exc
        except Exception as exc:
            raise AuthError(f"JWT token verification failed: {exc}") from exc

        sub = claims.get("sub")
        if not sub:
            raise InvalidTokenError("JWT token missing required 'sub' claim.")

        roles = frozenset(claims.get("roles", []))
        permissions = frozenset(claims.get("permissions", []))
        tenant_id = claims.get("tenant_id")

        return Identity(
            user_id=str(sub),
            roles=roles,
            permissions=permissions,
            tenant_id=str(tenant_id) if tenant_id is not None else None,
            claims=claims,
            is_authenticated=True,
        )


__all__ = [
    "JwtSecurityAdapter",
]
