"""Domain models and value objects for user management and social identity linking.

Notes/Architectural Intent:
    Encapsulates immutable models representing registered users, OAuth provider links,
    standardized social user claims, and ephemeral verification/reset tokens independently
    of specific storage engines or web frameworks.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any, Literal
from uuid import uuid4

from hexastack_auth.domain.models import Identity

TokenType = Literal["email_verification", "password_reset"]


@dataclass(frozen=True, slots=True)
class OAuthAccount:
    """Represents an external social identity linked to a domain user account.

    Notes/Architectural Intent:
        Stores third-party provider credentials (Google, GitHub, Microsoft)
        associated with a primary user account.
    """

    provider: str
    account_id: str
    user_id: str
    id: str = field(default_factory=lambda: str(uuid4()))
    account_email: str | None = None
    access_token: str | None = None
    refresh_token: str | None = None
    expires_at: int | None = None


@dataclass(frozen=True, slots=True)
class OAuthUserInfo:
    """Normalized profile claims extracted from an upstream OAuth2/OIDC provider.

    Notes/Architectural Intent:
        Harmonizes divergent claims schemas from Google, GitHub, and OIDC providers
        into a canonical domain representation.
    """

    provider: str
    account_id: str
    email: str
    name: str | None = None
    avatar_url: str | None = None
    claims: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class VerificationToken:
    """Cryptographic ephemeral token used for email verification or password reset flows.

    Notes/Architectural Intent:
        Time-bounded token tied to a specific user and purpose to prevent replay or misuse.
    """

    token: str
    user_id: str
    token_type: TokenType
    expires_at: datetime

    def is_expired(self) -> bool:
        """Check if the verification token has expired relative to current UTC time.

        Returns:
            True if current UTC time exceeds expires_at.
        """
        return datetime.now(UTC) >= self.expires_at


@dataclass(slots=True)
class User:
    """Domain aggregate representing a registered system user.

    Notes/Architectural Intent:
        Encapsulates credential verification status, role memberships, and external
        identity links. Provides a factory method to project into domain Identity.
    """

    email: str
    id: str = field(default_factory=lambda: str(uuid4()))
    hashed_password: str | None = None
    roles: frozenset[str] = field(default_factory=lambda: frozenset({"user"}))
    is_active: bool = True
    is_verified: bool = False
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    oauth_accounts: list[OAuthAccount] = field(default_factory=list)

    def to_identity(self) -> Identity:
        """Project the user aggregate into a security principal Identity.

        Returns:
            An authenticated Identity instance populated with user credentials and roles.
        """
        return Identity(
            user_id=self.id,
            roles=self.roles,
            claims={"email": self.email, "is_verified": self.is_verified},
            is_authenticated=self.is_active,
        )


__all__ = [
    "OAuthAccount",
    "OAuthUserInfo",
    "TokenType",
    "User",
    "VerificationToken",
]
