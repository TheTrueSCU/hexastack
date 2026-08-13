from hexastack_auth.domain.exceptions import (
    AuthError,
    InsufficientPermissionsError,
    InvalidCredentialsError,
    InvalidTokenError,
    PasswordHashError,
    TokenExpiredError,
)
from hexastack_core.domain.exceptions import (
    AuthenticationError,
    HexastackError,
    PermissionDeniedError,
)


def test_auth_exceptions_hierarchy():
    err = AuthError("Base auth error")
    assert isinstance(err, HexastackError)

    inv_cred = InvalidCredentialsError("Bad credentials")
    assert isinstance(inv_cred, AuthError)
    assert isinstance(inv_cred, AuthenticationError)

    inv_token = InvalidTokenError("Malformed token")
    assert isinstance(inv_token, AuthError)
    assert isinstance(inv_token, AuthenticationError)

    expired = TokenExpiredError("Token expired")
    assert isinstance(expired, AuthError)
    assert isinstance(expired, AuthenticationError)

    insuf_perm = InsufficientPermissionsError("Forbidden")
    assert isinstance(insuf_perm, AuthError)
    assert isinstance(insuf_perm, PermissionDeniedError)

    pwd_err = PasswordHashError("Hashing failed")
    assert isinstance(pwd_err, AuthError)
