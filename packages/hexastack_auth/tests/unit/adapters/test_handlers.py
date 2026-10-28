"""Unit tests for UserLifecycleHandlers CQRS adapter."""

from datetime import UTC, datetime, timedelta

import pytest

from hexastack_auth.adapters.handlers import UserLifecycleHandlers
from hexastack_auth.adapters.password import Pbkdf2PasswordHasher
from hexastack_auth.adapters.user_repository import (
    InMemoryTokenStore,
    InMemoryUserRepository,
)
from hexastack_auth.domain.commands import (
    AuthenticateUserQuery,
    OAuthLoginCommand,
    RegisterUserCommand,
    RequestPasswordResetCommand,
    ResetPasswordCommand,
    UpdateUserRoleCommand,
    VerifyEmailCommand,
)
from hexastack_auth.domain.exceptions import (
    AccountInactiveError,
    InvalidCredentialsError,
    InvalidTokenError,
    UserAlreadyExistsError,
    UserNotFoundError,
)
from hexastack_auth.domain.user import OAuthUserInfo, VerificationToken


@pytest.fixture
def user_repo() -> InMemoryUserRepository:
    return InMemoryUserRepository()


@pytest.fixture
def token_store() -> InMemoryTokenStore:
    return InMemoryTokenStore()


@pytest.fixture
def password_hasher() -> Pbkdf2PasswordHasher:
    return Pbkdf2PasswordHasher(iterations=10_000)


@pytest.fixture
def handlers(
    user_repo: InMemoryUserRepository,
    token_store: InMemoryTokenStore,
    password_hasher: Pbkdf2PasswordHasher,
) -> UserLifecycleHandlers:
    return UserLifecycleHandlers(
        user_repository=user_repo,
        token_store=token_store,
        password_hasher=password_hasher,
        token_lifetime_minutes=60,
    )


def test_register_user_success(
    handlers: UserLifecycleHandlers, user_repo: InMemoryUserRepository
):
    cmd = RegisterUserCommand(
        email="test@example.com",
        password="SecretPassword123!",  # pragma: allowlist secret
    )
    user, token = handlers.register_user(cmd)

    saved_user = user_repo.get_by_id(user.id)
    assert saved_user is not None
    assert saved_user.email == "test@example.com"
    assert saved_user.is_verified is False
    assert saved_user.is_active is True
    assert len(token) > 20


def test_register_user_duplicate_email_raises(handlers: UserLifecycleHandlers):
    cmd = RegisterUserCommand(
        email="dup@example.com",
        password="SecretPassword123!",  # pragma: allowlist secret
    )
    handlers.register_user(cmd)

    with pytest.raises(UserAlreadyExistsError) as exc_info:
        handlers.register_user(cmd)
    assert "dup@example.com" in str(exc_info.value)


@pytest.mark.asyncio
async def test_register_user_async(handlers: UserLifecycleHandlers):
    cmd = RegisterUserCommand(
        email="async@example.com",
        password="SecretPassword123!",  # pragma: allowlist secret
    )
    user, token = await handlers.register_user_async(cmd)

    assert user.email == "async@example.com"
    assert len(token) > 20


def test_verify_email_success(handlers: UserLifecycleHandlers):
    cmd = RegisterUserCommand(
        email="verify@example.com",
        password="SecretPassword123!",  # pragma: allowlist secret
    )
    user, token = handlers.register_user(cmd)
    assert user.is_verified is False

    verify_cmd = VerifyEmailCommand(token=token)
    verified_user = handlers.verify_email(verify_cmd)

    assert verified_user.id == user.id
    assert verified_user.is_verified is True


def test_verify_email_invalid_token(handlers: UserLifecycleHandlers):
    verify_cmd = VerifyEmailCommand(token="nonexistent_token")
    with pytest.raises(InvalidTokenError):
        handlers.verify_email(verify_cmd)


def test_verify_email_wrong_token_type(
    handlers: UserLifecycleHandlers, token_store: InMemoryTokenStore
):
    token = VerificationToken(
        token="some_reset_token",
        user_id="user-123",
        token_type="password_reset",
        expires_at=datetime.now(UTC) + timedelta(minutes=10),
    )
    token_store.store_token(token)

    verify_cmd = VerifyEmailCommand(token="some_reset_token")
    with pytest.raises(InvalidTokenError):
        handlers.verify_email(verify_cmd)


def test_verify_email_user_not_found(
    handlers: UserLifecycleHandlers,
    token_store: InMemoryTokenStore,
):
    token = VerificationToken(
        token="orphan_token",
        user_id="ghost_user_999",
        token_type="email_verification",
        expires_at=datetime.now(UTC) + timedelta(minutes=10),
    )
    token_store.store_token(token)

    verify_cmd = VerifyEmailCommand(token="orphan_token")
    with pytest.raises(UserNotFoundError):
        handlers.verify_email(verify_cmd)


@pytest.mark.asyncio
async def test_verify_email_async(handlers: UserLifecycleHandlers):
    cmd = RegisterUserCommand(
        email="async_verify@example.com",
        password="SecretPassword123!",  # pragma: allowlist secret
    )
    user, token = await handlers.register_user_async(cmd)

    verify_cmd = VerifyEmailCommand(token=token)
    verified_user = await handlers.verify_email_async(verify_cmd)

    assert verified_user.id == user.id
    assert verified_user.is_verified is True


def test_request_password_reset_existing_and_nonexistent(
    handlers: UserLifecycleHandlers,
):
    reg_cmd = RegisterUserCommand(
        email="reset@example.com",
        password="SecretPassword123!",  # pragma: allowlist secret
    )
    handlers.register_user(reg_cmd)

    reset_cmd = RequestPasswordResetCommand(email="reset@example.com")
    token = handlers.request_password_reset(reset_cmd)
    assert token is not None
    assert len(token) > 20

    # Nonexistent email returns None to prevent user enumeration
    unknown_cmd = RequestPasswordResetCommand(email="unknown@example.com")
    res_none = handlers.request_password_reset(unknown_cmd)
    assert res_none is None


@pytest.mark.asyncio
async def test_request_password_reset_async(handlers: UserLifecycleHandlers):
    reg_cmd = RegisterUserCommand(
        email="async_reset@example.com",
        password="SecretPassword123!",  # pragma: allowlist secret
    )
    await handlers.register_user_async(reg_cmd)

    reset_cmd = RequestPasswordResetCommand(email="async_reset@example.com")
    token = await handlers.request_password_reset_async(reset_cmd)
    assert token is not None


def test_reset_password_success(
    handlers: UserLifecycleHandlers,
    password_hasher: Pbkdf2PasswordHasher,
):
    reg_cmd = RegisterUserCommand(
        email="pwreset@example.com",
        password="OldPassword123!",  # pragma: allowlist secret
    )
    user, _ = handlers.register_user(reg_cmd)

    reset_token = handlers.request_password_reset(
        RequestPasswordResetCommand(email="pwreset@example.com")
    )
    assert reset_token is not None

    reset_cmd = ResetPasswordCommand(
        token=reset_token,
        new_password="NewSecretPassword456!",  # pragma: allowlist secret
    )
    updated_user = handlers.reset_password(reset_cmd)

    assert updated_user.id == user.id
    verified = password_hasher.verify_password(
        "NewSecretPassword456!",
        updated_user.hashed_password or "",  # pragma: allowlist secret
    )
    assert verified is True


def test_reset_password_invalid_token(handlers: UserLifecycleHandlers):
    reset_cmd = ResetPasswordCommand(
        token="invalid_token",
        new_password="NewPassword123!",  # pragma: allowlist secret
    )
    with pytest.raises(InvalidTokenError):
        handlers.reset_password(reset_cmd)


def test_reset_password_wrong_token_type(
    handlers: UserLifecycleHandlers, token_store: InMemoryTokenStore
):
    token = VerificationToken(
        token="verify_token_here",
        user_id="user-123",
        token_type="email_verification",
        expires_at=datetime.now(UTC) + timedelta(minutes=10),
    )
    token_store.store_token(token)

    reset_cmd = ResetPasswordCommand(
        token="verify_token_here",
        new_password="NewPassword123!",  # pragma: allowlist secret
    )
    with pytest.raises(InvalidTokenError):
        handlers.reset_password(reset_cmd)


def test_reset_password_user_not_found(
    handlers: UserLifecycleHandlers, token_store: InMemoryTokenStore
):
    token = VerificationToken(
        token="orphan_reset",
        user_id="missing_user",
        token_type="password_reset",
        expires_at=datetime.now(UTC) + timedelta(minutes=10),
    )
    token_store.store_token(token)

    reset_cmd = ResetPasswordCommand(
        token="orphan_reset",
        new_password="NewPassword123!",  # pragma: allowlist secret
    )
    with pytest.raises(UserNotFoundError):
        handlers.reset_password(reset_cmd)


@pytest.mark.asyncio
async def test_reset_password_async(handlers: UserLifecycleHandlers):
    reg_cmd = RegisterUserCommand(
        email="async_pwreset@example.com",
        password="OldPassword123!",  # pragma: allowlist secret
    )
    await handlers.register_user_async(reg_cmd)

    reset_token = await handlers.request_password_reset_async(
        RequestPasswordResetCommand(email="async_pwreset@example.com")
    )
    assert reset_token is not None

    reset_cmd = ResetPasswordCommand(
        token=reset_token,
        new_password="NewAsyncPassword456!",  # pragma: allowlist secret
    )
    updated_user = await handlers.reset_password_async(reset_cmd)
    assert updated_user.email == "async_pwreset@example.com"


def test_authenticate_user_success_and_failures(
    handlers: UserLifecycleHandlers, user_repo: InMemoryUserRepository
):
    reg_cmd = RegisterUserCommand(
        email="auth_user@example.com",
        password="CorrectPassword123!",  # pragma: allowlist secret
    )
    user, _ = handlers.register_user(reg_cmd)

    # 1. Success
    query = AuthenticateUserQuery(
        email="auth_user@example.com",
        password="CorrectPassword123!",  # pragma: allowlist secret
    )
    auth_user = handlers.authenticate_user(query)
    assert auth_user.id == user.id

    # 2. Wrong password
    wrong_query = AuthenticateUserQuery(
        email="auth_user@example.com",
        password="WrongPassword!",  # pragma: allowlist secret
    )
    with pytest.raises(InvalidCredentialsError):
        handlers.authenticate_user(wrong_query)

    # 3. Nonexistent user
    unknown_query = AuthenticateUserQuery(
        email="unknown@example.com",
        password="AnyPassword123!",  # pragma: allowlist secret
    )
    with pytest.raises(InvalidCredentialsError):
        handlers.authenticate_user(unknown_query)

    # 4. User without hashed password
    user.hashed_password = None
    user_repo.save(user)
    with pytest.raises(InvalidCredentialsError):
        handlers.authenticate_user(query)

    # 5. Inactive user
    handlers.password_hasher.hash_password(
        "CorrectPassword123!"  # pragma: allowlist secret
    )
    user.hashed_password = handlers.password_hasher.hash_password(
        "CorrectPassword123!"  # pragma: allowlist secret
    )
    user.is_active = False
    user_repo.save(user)
    with pytest.raises(AccountInactiveError):
        handlers.authenticate_user(query)


@pytest.mark.asyncio
async def test_authenticate_user_async(handlers: UserLifecycleHandlers):
    reg_cmd = RegisterUserCommand(
        email="async_auth@example.com",
        password="AsyncPassword123!",  # pragma: allowlist secret
    )
    await handlers.register_user_async(reg_cmd)

    query = AuthenticateUserQuery(
        email="async_auth@example.com",
        password="AsyncPassword123!",  # pragma: allowlist secret
    )
    auth_user = await handlers.authenticate_user_async(query)
    assert auth_user.email == "async_auth@example.com"


def test_update_user_role_success_and_not_found(handlers: UserLifecycleHandlers):
    reg_cmd = RegisterUserCommand(
        email="role_user@example.com",
        password="Password123!",  # pragma: allowlist secret
    )
    user, _ = handlers.register_user(reg_cmd)
    assert user.roles == frozenset({"user"})

    update_cmd = UpdateUserRoleCommand(
        user_id=user.id, roles=frozenset({"user", "admin"})
    )
    updated_user = handlers.update_user_role(update_cmd)
    assert updated_user.roles == frozenset({"user", "admin"})

    unknown_cmd = UpdateUserRoleCommand(
        user_id="missing_id", roles=frozenset({"admin"})
    )
    with pytest.raises(UserNotFoundError):
        handlers.update_user_role(unknown_cmd)


@pytest.mark.asyncio
async def test_update_user_role_async(handlers: UserLifecycleHandlers):
    reg_cmd = RegisterUserCommand(
        email="async_role@example.com",
        password="Password123!",  # pragma: allowlist secret
    )
    user, _ = await handlers.register_user_async(reg_cmd)

    update_cmd = UpdateUserRoleCommand(user_id=user.id, roles=frozenset({"manager"}))
    updated_user = await handlers.update_user_role_async(update_cmd)
    assert updated_user.roles == frozenset({"manager"})


def test_oauth_login_flow(
    handlers: UserLifecycleHandlers, user_repo: InMemoryUserRepository
):
    # Case 1: Brand new user via OAuth
    oauth_info = OAuthUserInfo(
        provider="google",
        account_id="google-sub-12345",
        email="google_user@example.com",
        name="Google User",
    )
    cmd = OAuthLoginCommand(provider="google", oauth_user=oauth_info)
    user1 = handlers.oauth_login(cmd)

    assert user1.email == "google_user@example.com"
    assert user1.is_verified is True
    assert user1.is_active is True
    assert len(user1.oauth_accounts) == 1
    assert user1.oauth_accounts[0].provider == "google"
    assert user1.oauth_accounts[0].account_id == "google-sub-12345"

    # Case 2: Subsequent login with same OAuth account (returns existing)
    user2 = handlers.oauth_login(cmd)
    assert user2.id == user1.id

    # Case 3: Existing password user links a new OAuth provider
    pwd_cmd = RegisterUserCommand(
        email="existing@example.com",
        password="Password123!",  # pragma: allowlist secret
    )
    pwd_user, _ = handlers.register_user(pwd_cmd)

    github_info = OAuthUserInfo(
        provider="github",
        account_id="gh-998877",
        email="existing@example.com",
        name="Existing GitHub",
    )
    link_cmd = OAuthLoginCommand(provider="github", oauth_user=github_info)
    linked_user = handlers.oauth_login(link_cmd)

    assert linked_user.id == pwd_user.id
    assert any(acc.provider == "github" for acc in linked_user.oauth_accounts)


@pytest.mark.asyncio
async def test_oauth_login_async(handlers: UserLifecycleHandlers):
    oauth_info = OAuthUserInfo(
        provider="github",
        account_id="gh-async-1",
        email="gh_async@example.com",
    )
    cmd = OAuthLoginCommand(provider="github", oauth_user=oauth_info)
    user = await handlers.oauth_login_async(cmd)
    assert user.email == "gh_async@example.com"
