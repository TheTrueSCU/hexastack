from hexastack_auth.domain.commands import (
    AuthenticateUserQuery,
    OAuthLoginCommand,
    RegisterUserCommand,
    RequestPasswordResetCommand,
    ResetPasswordCommand,
    UpdateUserRoleCommand,
    VerifyEmailCommand,
)
from hexastack_auth.domain.user import OAuthUserInfo


def test_commands_and_queries_instantiation():
    reg = RegisterUserCommand(
        email="alice@example.com",
        password="SecretPassword123",  # pragma: allowlist secret
    )
    assert reg.email == "alice@example.com"
    assert reg.password == "SecretPassword123"  # pragma: allowlist secret
    assert reg.roles == frozenset({"user"})
    assert reg.is_active is True
    assert reg.is_verified is False

    ver = VerifyEmailCommand(token="token-abc")
    assert ver.token == "token-abc"

    req_reset = RequestPasswordResetCommand(email="alice@example.com")
    assert req_reset.email == "alice@example.com"

    reset = ResetPasswordCommand(
        token="token-reset",
        new_password="NewSecretPassword123",  # pragma: allowlist secret
    )
    assert reset.token == "token-reset"
    assert reset.new_password == "NewSecretPassword123"  # pragma: allowlist secret

    auth_q = AuthenticateUserQuery(
        email="alice@example.com",
        password="SecretPassword123",  # pragma: allowlist secret
    )
    assert auth_q.email == "alice@example.com"
    assert auth_q.password == "SecretPassword123"  # pragma: allowlist secret

    upd_role = UpdateUserRoleCommand(
        user_id="user-123", roles=frozenset({"admin", "editor"})
    )
    assert upd_role.user_id == "user-123"
    assert upd_role.roles == frozenset({"admin", "editor"})

    oauth_cmd = OAuthLoginCommand(
        provider="github",
        oauth_user=OAuthUserInfo(
            provider="github", account_id="gh-1", email="gh@user.com"
        ),
    )
    assert oauth_cmd.provider == "github"
    assert oauth_cmd.oauth_user.email == "gh@user.com"
