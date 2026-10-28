from hexastack_auth.domain.exceptions import (
    AccountInactiveError,
    AuthError,
    InsufficientPermissionsError,
    InvalidCredentialsError,
    InvalidTokenError,
    OAuthProviderError,
    PasswordHashError,
    TokenExpiredError,
    UserAlreadyExistsError,
    UserNotFoundError,
)
from hexastack_core.domain.exceptions import (
    AuthenticationError,
    HexastackError,
    PermissionDeniedError,
)


def test_auth_exceptions_hierarchy():
    err = AuthError("Base auth error")
    is_hex = isinstance(err, HexastackError)
    assert is_hex is True

    inv_cred = InvalidCredentialsError("Bad credentials")
    is_auth_err = isinstance(inv_cred, AuthError)
    assert is_auth_err is True
    is_authent = isinstance(inv_cred, AuthenticationError)
    assert is_authent is True

    inv_token = InvalidTokenError("Malformed token")
    is_tok = isinstance(inv_token, AuthError)
    assert is_tok is True

    expired = TokenExpiredError("Token expired")
    is_exp = isinstance(expired, AuthError)
    assert is_exp is True

    insuf_perm = InsufficientPermissionsError("Forbidden")
    is_perm = isinstance(insuf_perm, PermissionDeniedError)
    assert is_perm is True

    pwd_err = PasswordHashError("Hashing failed")
    is_pwd = isinstance(pwd_err, AuthError)
    assert is_pwd is True

    uae = UserAlreadyExistsError("test@example.com")
    assert uae.email == "test@example.com"
    msg_uae = str(uae)
    assert msg_uae == "User with email 'test@example.com' already exists."

    unf = UserNotFoundError("user-123")
    assert unf.identifier == "user-123"
    msg_unf = str(unf)
    assert msg_unf == "User 'user-123' not found."

    act = AccountInactiveError("user-456")
    assert act.user_id == "user-456"
    msg_act = str(act)
    assert msg_act == "Account for user 'user-456' is deactivated."

    oauth_err = OAuthProviderError("google", "Token exchange failed")
    assert oauth_err.provider == "google"
    msg_oauth = str(oauth_err)
    assert msg_oauth == "OAuth2 provider 'google' error: Token exchange failed"
