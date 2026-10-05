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


__all__ = [
    "AuthError",
    "InsufficientPermissionsError",
    "InvalidCredentialsError",
    "InvalidTokenError",
    "PasswordHashError",
    "TokenExpiredError",
]
