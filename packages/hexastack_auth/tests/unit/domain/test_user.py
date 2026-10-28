from datetime import UTC, datetime, timedelta

from hexastack_auth.domain.user import (
    OAuthAccount,
    OAuthUserInfo,
    User,
    VerificationToken,
)


def test_oauth_account_instantiation():
    acc = OAuthAccount(
        provider="github",
        account_id="12345",
        user_id="user-1",
        account_email="dev@github.com",
    )
    assert acc.provider == "github"
    assert acc.account_id == "12345"
    assert acc.user_id == "user-1"
    assert acc.account_email == "dev@github.com"


def test_oauth_user_info_instantiation():
    info = OAuthUserInfo(
        provider="google",
        account_id="g-999",
        email="alex@gmail.com",
        name="Alex Smith",
        avatar_url="https://avatar.com/alex.png",
        claims={"hd": "gmail.com"},
    )
    assert info.provider == "google"
    assert info.account_id == "g-999"
    assert info.email == "alex@gmail.com"
    assert info.name == "Alex Smith"
    assert info.avatar_url == "https://avatar.com/alex.png"
    assert info.claims == {"hd": "gmail.com"}


def test_verification_token_expiration():
    future = datetime.now(UTC) + timedelta(minutes=10)
    token_valid = VerificationToken(
        token="valid-tok",
        user_id="u1",
        token_type="email_verification",
        expires_at=future,
    )
    is_exp = token_valid.is_expired()
    assert is_exp is False

    past = datetime.now(UTC) - timedelta(minutes=5)
    token_expired = VerificationToken(
        token="old-tok",
        user_id="u1",
        token_type="password_reset",
        expires_at=past,
    )
    is_exp_past = token_expired.is_expired()
    assert is_exp_past is True


def test_user_aggregate_to_identity():
    user = User(
        email="sam@example.com",
        roles=frozenset({"admin", "user"}),
        is_active=True,
        is_verified=True,
    )
    ident = user.to_identity()
    assert ident.user_id == user.id
    assert ident.roles == frozenset({"admin", "user"})
    is_admin = ident.has_role("admin")
    assert is_admin is True
    is_auth = ident.is_authenticated
    assert is_auth is True
    assert ident.claims["email"] == "sam@example.com"
    assert ident.claims["is_verified"] is True
