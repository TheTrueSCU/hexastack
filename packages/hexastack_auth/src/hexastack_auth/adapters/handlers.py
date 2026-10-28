"""CQRS command and query handler implementations for user lifecycle workflows.

Notes/Architectural Intent:
    Orchestrates user registration, email verification, password recovery,
    credential verification, and social OAuth account linking. Works with any
    UserRepositoryPort, TokenStorePort, and PasswordHasherPort implementation.
"""

from __future__ import annotations

import asyncio
import secrets
from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING

from hexastack_auth.adapters.password import Pbkdf2PasswordHasher
from hexastack_auth.adapters.user_repository import (
    InMemoryTokenStore,
    InMemoryUserRepository,
)
from hexastack_auth.domain.exceptions import (
    AccountInactiveError,
    InvalidCredentialsError,
    InvalidTokenError,
    UserAlreadyExistsError,
    UserNotFoundError,
)
from hexastack_auth.domain.user import (
    OAuthAccount,
    User,
    VerificationToken,
)

if TYPE_CHECKING:
    from hexastack_auth.domain.commands import (
        AuthenticateUserQuery,
        OAuthLoginCommand,
        RegisterUserCommand,
        RequestPasswordResetCommand,
        ResetPasswordCommand,
        UpdateUserRoleCommand,
        VerifyEmailCommand,
    )
    from hexastack_auth.ports.password import PasswordHasherPort
    from hexastack_auth.ports.user import TokenStorePort, UserRepositoryPort


class UserLifecycleHandlers:
    """CQRS handler coordinating domain user lifecycle operations.

    Notes/Architectural Intent:
        Encapsulates application logic for authentication, email verification,
        and password recovery, remaining completely decoupled from web/transport frameworks.
    """

    def __init__(
        self,
        user_repository: UserRepositoryPort | None = None,
        token_store: TokenStorePort | None = None,
        password_hasher: PasswordHasherPort | None = None,
        token_lifetime_minutes: int = 60,
    ) -> None:
        """Initialize UserLifecycleHandlers.

        Args:
            user_repository: UserRepositoryPort implementation (defaults to InMemoryUserRepository).
            token_store: TokenStorePort implementation (defaults to InMemoryTokenStore).
            password_hasher: PasswordHasherPort implementation (defaults to Pbkdf2PasswordHasher).
            token_lifetime_minutes: Time-to-live for issued verification/reset tokens.
        """
        self.user_repository = user_repository or InMemoryUserRepository()
        self.token_store = token_store or InMemoryTokenStore()
        self.password_hasher = password_hasher or Pbkdf2PasswordHasher()
        self.token_lifetime = timedelta(minutes=token_lifetime_minutes)

    def register_user(self, cmd: RegisterUserCommand) -> tuple[User, str]:
        """Execute user registration and issue an email verification token.

        Args:
            cmd: RegisterUserCommand containing registration details.

        Returns:
            Tuple of (persisted User, raw verification token string).

        Raises:
            UserAlreadyExistsError: If the email is already registered.
        """
        existing = self.user_repository.get_by_email(cmd.email)
        if existing is not None:
            raise UserAlreadyExistsError(cmd.email)

        hashed_pw = self.password_hasher.hash_password(cmd.password)
        user = User(
            email=cmd.email,
            hashed_password=hashed_pw,
            roles=cmd.roles,
            is_active=cmd.is_active,
            is_verified=cmd.is_verified,
        )
        saved_user = self.user_repository.save(user)

        token_str = secrets.token_urlsafe(32)
        v_token = VerificationToken(
            token=token_str,
            user_id=saved_user.id,
            token_type="email_verification",
            expires_at=datetime.now(UTC) + self.token_lifetime,
        )
        self.token_store.store_token(v_token)
        return saved_user, token_str

    async def register_user_async(self, cmd: RegisterUserCommand) -> tuple[User, str]:
        """Asynchronously execute user registration."""
        return await asyncio.to_thread(self.register_user, cmd)

    def verify_email(self, cmd: VerifyEmailCommand) -> User:
        """Validate email verification token and transition user to verified state.

        Args:
            cmd: VerifyEmailCommand containing token string.

        Returns:
            Updated verified User instance.

        Raises:
            InvalidTokenError: If token is nonexistent or expired.
            UserNotFoundError: If associated user record is missing.
        """
        v_token = self.token_store.consume_token(cmd.token)
        if v_token is None or v_token.token_type != "email_verification":  # noqa: S105
            raise InvalidTokenError("Verification token is invalid or has expired.")

        user = self.user_repository.get_by_id(v_token.user_id)
        if user is None:
            raise UserNotFoundError(v_token.user_id)

        user.is_verified = True
        return self.user_repository.save(user)

    async def verify_email_async(self, cmd: VerifyEmailCommand) -> User:
        """Asynchronously validate email verification token."""
        return await asyncio.to_thread(self.verify_email, cmd)

    def request_password_reset(self, cmd: RequestPasswordResetCommand) -> str | None:
        """Generate a password reset token if the target email is registered.

        Args:
            cmd: RequestPasswordResetCommand with target email.

        Returns:
            Reset token string if user exists, None otherwise (prevents user enumeration).
        """
        user = self.user_repository.get_by_email(cmd.email)
        if user is None:
            return None

        token_str = secrets.token_urlsafe(32)
        reset_token = VerificationToken(
            token=token_str,
            user_id=user.id,
            token_type="password_reset",
            expires_at=datetime.now(UTC) + self.token_lifetime,
        )
        self.token_store.store_token(reset_token)
        return token_str

    async def request_password_reset_async(
        self, cmd: RequestPasswordResetCommand
    ) -> str | None:
        """Asynchronously generate a password reset token."""
        return await asyncio.to_thread(self.request_password_reset, cmd)

    def reset_password(self, cmd: ResetPasswordCommand) -> User:
        """Execute password update using a valid reset token.

        Args:
            cmd: ResetPasswordCommand with token and new password.

        Returns:
            Updated User instance.

        Raises:
            InvalidTokenError: If token is invalid or expired.
            UserNotFoundError: If target user is missing.
        """
        reset_token = self.token_store.consume_token(cmd.token)
        if reset_token is None or reset_token.token_type != "password_reset":  # noqa: S105
            raise InvalidTokenError("Password reset token is invalid or has expired.")

        user = self.user_repository.get_by_id(reset_token.user_id)
        if user is None:
            raise UserNotFoundError(reset_token.user_id)

        user.hashed_password = self.password_hasher.hash_password(cmd.new_password)
        return self.user_repository.save(user)

    async def reset_password_async(self, cmd: ResetPasswordCommand) -> User:
        """Asynchronously execute password update."""
        return await asyncio.to_thread(self.reset_password, cmd)

    def authenticate_user(self, query: AuthenticateUserQuery) -> User:
        """Verify user credentials and return the authenticated User aggregate.

        Args:
            query: AuthenticateUserQuery containing email and password.

        Returns:
            Authenticated User instance.

        Raises:
            InvalidCredentialsError: If credentials do not match or account has no password.
            AccountInactiveError: If account is deactivated.
        """
        user = self.user_repository.get_by_email(query.email)
        if user is None or not user.hashed_password:
            raise InvalidCredentialsError("Invalid email or password.")

        if not user.is_active:
            raise AccountInactiveError(user.id)

        matched = self.password_hasher.verify_password(
            query.password, user.hashed_password
        )
        if not matched:
            raise InvalidCredentialsError("Invalid email or password.")

        return user

    async def authenticate_user_async(self, query: AuthenticateUserQuery) -> User:
        """Asynchronously verify user credentials."""
        return await asyncio.to_thread(self.authenticate_user, query)

    def update_user_role(self, cmd: UpdateUserRoleCommand) -> User:
        """Update role assignments of an existing user.

        Args:
            cmd: UpdateUserRoleCommand specifying user ID and target roles.

        Returns:
            Updated User instance.

        Raises:
            UserNotFoundError: If user ID is not found.
        """
        user = self.user_repository.get_by_id(cmd.user_id)
        if user is None:
            raise UserNotFoundError(cmd.user_id)

        user.roles = cmd.roles
        return self.user_repository.save(user)

    async def update_user_role_async(self, cmd: UpdateUserRoleCommand) -> User:
        """Asynchronously update role assignments."""
        return await asyncio.to_thread(self.update_user_role, cmd)

    def oauth_login(self, cmd: OAuthLoginCommand) -> User:
        """Authenticate user via third-party OAuth profile or auto-provision account.

        Args:
            cmd: OAuthLoginCommand with provider name and profile claims.

        Returns:
            Authenticated or newly provisioned User instance.
        """
        # 1. Check if linked account exists
        existing_by_oauth = self.user_repository.get_by_oauth(
            cmd.provider,
            cmd.oauth_user.account_id,
        )
        if existing_by_oauth is not None:
            return existing_by_oauth

        # 2. Check if user with same email exists
        user = self.user_repository.get_by_email(cmd.oauth_user.email)
        if user is None:
            # Provision new user account
            user = User(
                email=cmd.oauth_user.email,
                is_active=True,
                is_verified=True,
            )
            user = self.user_repository.save(user)

        # Link external account
        oauth_acc = OAuthAccount(
            provider=cmd.provider,
            account_id=cmd.oauth_user.account_id,
            user_id=user.id,
            account_email=cmd.oauth_user.email,
        )
        user.oauth_accounts.append(oauth_acc)
        return self.user_repository.save(user)

    async def oauth_login_async(self, cmd: OAuthLoginCommand) -> User:
        """Asynchronously authenticate via third-party OAuth profile."""
        return await asyncio.to_thread(self.oauth_login, cmd)


__all__ = [
    "UserLifecycleHandlers",
]
