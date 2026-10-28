from hexastack_core.domain.exceptions import (
    AuthenticationError,
    HexastackError,
    PermissionDeniedError,
)


class AuthError(HexastackError):
    """Base domain exception for all authentication and authorization errors.

    Notes/Architectural Intent:
        Inherits from HexastackError to allow global exception handlers across
        transports (HTTP, gRPC, GraphQL) to catch security errors uniformly.
    """


class InvalidCredentialsError(AuthenticationError, AuthError):
    """Exception raised when supplied credentials (username/password/key) are invalid.

    Notes/Architectural Intent:
        Extends AuthenticationError to trigger 401 Unauthorized at the HTTP boundary.
    """


class InvalidTokenError(AuthenticationError, AuthError):
    """Exception raised when a bearer or JWT token is malformed or signature is invalid.

    Notes/Architectural Intent:
        Ensures tampered or unparseable security tokens fail fast with clear diagnostics.
    """


class TokenExpiredError(AuthenticationError, AuthError):
    """Exception raised when a cryptographic security token has expired.

    Notes/Architectural Intent:
        Differentiates expired tokens from invalid signatures to allow clients
        to trigger token refresh flows.
    """


class InsufficientPermissionsError(PermissionDeniedError, AuthError):
    """Exception raised when an authenticated identity lacks required roles or permissions.

    Notes/Architectural Intent:
        Extends PermissionDeniedError to trigger 403 Forbidden at the presentation boundary.
    """


class PasswordHashError(AuthError):
    """Exception raised when password hashing or verification computation fails.

    Notes/Architectural Intent:
        Shields internal cryptographic backend errors from leaking sensitive details.
    """


class InvalidWebhookSignatureError(AuthenticationError, AuthError):
    """Exception raised when an inbound webhook signature header fails cryptographic verification.

    Notes/Architectural Intent:
        Extends AuthenticationError to trigger 401 Unauthorized at HTTP boundaries
        when incoming webhooks fail HMAC or vendor signature validity checks.
    """


class WebhookReplayError(AuthenticationError, AuthError):
    """Exception raised when an inbound webhook timestamp exceeds allowable replay tolerance.

    Notes/Architectural Intent:
        Prevents replay attacks by rejecting webhooks whose signed timestamp is too old or
        drifted into the future.
    """


class UserAlreadyExistsError(AuthError):
    """Exception raised when registering a user with an already registered email.

    Notes/Architectural Intent:
        Prevents duplicate user accounts and signals registration conflict.
    """

    def __init__(self, email: str) -> None:
        """Initialize with conflicting email.

        Args:
            email: Conflicting email address.
        """
        self.email = email
        super().__init__(f"User with email '{email}' already exists.")


class UserNotFoundError(AuthError):
    """Exception raised when a requested user cannot be found by ID or email.

    Notes/Architectural Intent:
        Provides clear domain diagnostics when querying nonexistent user records.
    """

    def __init__(self, identifier: str) -> None:
        """Initialize with user identifier.

        Args:
            identifier: User ID or email searched.
        """
        self.identifier = identifier
        super().__init__(f"User '{identifier}' not found.")


class AccountInactiveError(AuthError):
    """Exception raised when an inactive or deactivated user attempts authentication.

    Notes/Architectural Intent:
        Enforces user deactivation state across login and credential checks.
    """

    def __init__(self, user_id: str) -> None:
        """Initialize with deactivated user ID.

        Args:
            user_id: Deactivated user identifier.
        """
        self.user_id = user_id
        super().__init__(f"Account for user '{user_id}' is deactivated.")


class OAuthProviderError(AuthError):
    """Exception raised when an upstream OAuth2/OIDC provider interaction fails.

    Notes/Architectural Intent:
        Encapsulates token exchange or user-info retrieval failures from external IdPs.
    """

    def __init__(self, provider: str, message: str) -> None:
        """Initialize with provider name and failure message.

        Args:
            provider: Identity provider name (e.g. 'google', 'github').
            message: Descriptive failure message.
        """
        self.provider = provider
        super().__init__(f"OAuth2 provider '{provider}' error: {message}")


__all__ = [
    "AccountInactiveError",
    "AuthError",
    "InsufficientPermissionsError",
    "InvalidCredentialsError",
    "InvalidTokenError",
    "InvalidWebhookSignatureError",
    "OAuthProviderError",
    "PasswordHashError",
    "TokenExpiredError",
    "UserAlreadyExistsError",
    "UserNotFoundError",
    "WebhookReplayError",
]
