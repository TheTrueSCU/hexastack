"""CQRS command and query message definitions for user lifecycle and authentication.

Notes/Architectural Intent:
    Encapsulates immutable CQRS commands and queries representing user onboarding,
    credential verification, password recovery, and role modification independently
    of presentation protocols (REST, CLI, gRPC).
"""

from __future__ import annotations

from dataclasses import dataclass, field

from hexastack_auth.domain.user import OAuthUserInfo


@dataclass(frozen=True, slots=True)
class RegisterUserCommand:
    """Command requesting registration of a new user account with credentials.

    Notes/Architectural Intent:
        Initiates user creation and optional email verification token issuance.
    """

    email: str
    password: str
    roles: frozenset[str] = field(default_factory=lambda: frozenset({"user"}))
    is_active: bool = True
    is_verified: bool = False


@dataclass(frozen=True, slots=True)
class VerifyEmailCommand:
    """Command requesting verification of a user's email address via token.

    Notes/Architectural Intent:
        Validates token expiration and transitions the target user to is_verified=True.
    """

    token: str


@dataclass(frozen=True, slots=True)
class RequestPasswordResetCommand:
    """Command initiating the password recovery workflow for a given email.

    Notes/Architectural Intent:
        Generates an ephemeral password reset token if the target email exists.
    """

    email: str


@dataclass(frozen=True, slots=True)
class ResetPasswordCommand:
    """Command executing password update using a validated reset token.

    Notes/Architectural Intent:
        Consumes the reset token and cryptographically updates the user password.
    """

    token: str
    new_password: str


@dataclass(frozen=True, slots=True)
class AuthenticateUserQuery:
    """Query verifying user credentials and retrieving an authenticated Identity.

    Notes/Architectural Intent:
        Performs password hash verification and returns the authenticated user aggregate.
    """

    email: str
    password: str


@dataclass(frozen=True, slots=True)
class UpdateUserRoleCommand:
    """Command modifying the role assignments of an existing user.

    Notes/Architectural Intent:
        Enforces administrative RBAC policy updates on target identities.
    """

    user_id: str
    roles: frozenset[str]


@dataclass(frozen=True, slots=True)
class OAuthLoginCommand:
    """Command executing social identity authentication or automatic user provisioning.

    Notes/Architectural Intent:
        Locates existing account by provider link or creates a new user from provider claims.
    """

    provider: str
    oauth_user: OAuthUserInfo


__all__ = [
    "AuthenticateUserQuery",
    "OAuthLoginCommand",
    "RegisterUserCommand",
    "RequestPasswordResetCommand",
    "ResetPasswordCommand",
    "UpdateUserRoleCommand",
    "VerifyEmailCommand",
]
