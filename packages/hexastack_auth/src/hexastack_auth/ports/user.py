"""Abstract ports for user repository storage, token persistence, and OAuth2 identity providers.

Notes/Architectural Intent:
    Defines abstract contracts isolating domain user management and OAuth authentication
    from specific persistence technologies (in-memory, SQLAlchemy) and third-party API clients.
"""

from __future__ import annotations

import secrets
from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Any

from hexastack_auth.domain.oidc import (
    OAuthAuthorizationRequest,
    generate_oidc_nonce,
    generate_pkce_pair,
)

if TYPE_CHECKING:
    from hexastack_auth.domain.user import OAuthUserInfo, User, VerificationToken


class UserRepositoryPort(ABC):
    """Abstract port for persisting and querying user domain aggregates.

    Notes/Architectural Intent:
        Enables storage-agnostic CRUD operations for user accounts and linked social identities.
    """

    @abstractmethod
    def get_by_id(self, user_id: str) -> User | None:
        """Retrieve a user by unique identifier string.

        Args:
            user_id: Target user unique ID.

        Returns:
            The User instance if found, None otherwise.
        """

    @abstractmethod
    async def get_by_id_async(self, user_id: str) -> User | None:
        """Asynchronously retrieve a user by unique identifier string.

        Args:
            user_id: Target user unique ID.

        Returns:
            The User instance if found, None otherwise.
        """

    @abstractmethod
    def get_by_email(self, email: str) -> User | None:
        """Retrieve a user by email address.

        Args:
            email: Target email string.

        Returns:
            The User instance if found, None otherwise.
        """

    @abstractmethod
    async def get_by_email_async(self, email: str) -> User | None:
        """Asynchronously retrieve a user by email address.

        Args:
            email: Target email string.

        Returns:
            The User instance if found, None otherwise.
        """

    @abstractmethod
    def get_by_oauth(self, provider: str, account_id: str) -> User | None:
        """Retrieve a user linked to a specific third-party OAuth account.

        Args:
            provider: Identity provider name (e.g. 'google', 'github').
            account_id: Provider-specific subject or account ID.

        Returns:
            The linked User instance if found, None otherwise.
        """

    @abstractmethod
    async def get_by_oauth_async(self, provider: str, account_id: str) -> User | None:
        """Asynchronously retrieve a user linked to a third-party OAuth account.

        Args:
            provider: Identity provider name.
            account_id: Provider-specific subject or account ID.

        Returns:
            The linked User instance if found, None otherwise.
        """

    @abstractmethod
    def save(self, user: User) -> User:
        """Persist or update a user aggregate in storage.

        Args:
            user: User domain aggregate to persist.

        Returns:
            The saved User instance.
        """

    @abstractmethod
    async def save_async(self, user: User) -> User:
        """Asynchronously persist or update a user aggregate.

        Args:
            user: User domain aggregate to persist.

        Returns:
            The saved User instance.
        """

    @abstractmethod
    def delete(self, user_id: str) -> bool:
        """Delete a user account by unique identifier.

        Args:
            user_id: Target user unique ID.

        Returns:
            True if the record was removed, False if nonexistent.
        """

    @abstractmethod
    async def delete_async(self, user_id: str) -> bool:
        """Asynchronously delete a user account by unique identifier.

        Args:
            user_id: Target user unique ID.

        Returns:
            True if the record was removed, False if nonexistent.
        """


class TokenStorePort(ABC):
    """Abstract port for storing and consuming ephemeral verification/reset tokens.

    Notes/Architectural Intent:
        Decouples token lifecycle management from cache or database backends.
    """

    @abstractmethod
    def store_token(self, token: VerificationToken) -> None:
        """Store an ephemeral verification token.

        Args:
            token: VerificationToken instance.
        """

    @abstractmethod
    async def store_token_async(self, token: VerificationToken) -> None:
        """Asynchronously store an ephemeral verification token.

        Args:
            token: VerificationToken instance.
        """

    @abstractmethod
    def get_token(self, token: str) -> VerificationToken | None:
        """Lookup an active verification token.

        Args:
            token: Token string.

        Returns:
            The VerificationToken if active, None if expired or missing.
        """

    @abstractmethod
    async def get_token_async(self, token: str) -> VerificationToken | None:
        """Asynchronously lookup an active verification token.

        Args:
            token: Token string.

        Returns:
            The VerificationToken if active, None if expired or missing.
        """

    @abstractmethod
    def consume_token(self, token: str) -> VerificationToken | None:
        """Retrieve and immediately invalidate a single-use verification token.

        Args:
            token: Token string to consume.

        Returns:
            The VerificationToken if valid and not expired, None otherwise.
        """

    @abstractmethod
    async def consume_token_async(self, token: str) -> VerificationToken | None:
        """Asynchronously retrieve and invalidate a single-use verification token.

        Args:
            token: Token string to consume.

        Returns:
            The VerificationToken if valid and not expired, None otherwise.
        """


class OAuthProviderPort(ABC):
    """Abstract port for communicating with an external OAuth2 / OIDC identity provider.

    Notes/Architectural Intent:
        Standardizes authorization redirect construction and code-to-claims token exchanges.
    """

    @property
    @abstractmethod
    def name(self) -> str:
        """Canonical name identifier of the provider (e.g. 'google', 'github')."""

    @abstractmethod
    def get_authorization_url(
        self,
        state: str,
        redirect_uri: str,
        *,
        code_challenge: str | None = None,
        code_challenge_method: str | None = None,
        nonce: str | None = None,
    ) -> str:
        """Generate the external provider's login authorization URL.

        Args:
            state: Cryptographic anti-CSRF state parameter.
            redirect_uri: Registered callback URL on the application server.
            code_challenge: Optional PKCE code challenge string (S256).
            code_challenge_method: Optional PKCE challenge method (``'S256'``).
            nonce: Optional OIDC ID-token binding nonce.

        Returns:
            Full HTTPS authorization URL to redirect user agent.
        """

    def create_authorization_request(
        self,
        redirect_uri: str,
        *,
        state: str | None = None,
        use_pkce: bool = True,
        use_nonce: bool = True,
    ) -> OAuthAuthorizationRequest:
        """Construct a stateful authorization redirect bundle with PKCE and OIDC nonce.

        Args:
            redirect_uri: Registered callback URL on the application server.
            state: Optional explicit anti-CSRF state (CSPRNG generated if omitted).
            use_pkce: Whether to attach an RFC 7636 ``S256`` PKCE challenge pair.
            use_nonce: Whether to attach a CSPRNG OIDC nonce parameter.

        Returns:
            ``OAuthAuthorizationRequest`` containing redirect URL, ``state``,
            and ephemeral ``code_verifier`` / ``nonce`` secrets.

        Notes/Architectural Intent:
            Concrete helper on ``OAuthProviderPort`` so existing providers only
            implementing the three abstract members gain PKCE and nonce generation
            without altering ``OAuthProviderPort.__abstractmethods__``.
        """
        resolved_state = state or secrets.token_urlsafe(24)
        code_verifier: str | None = None
        code_challenge: str | None = None
        code_challenge_method: str | None = None
        extra_kwargs: dict[str, Any] = {}

        if use_pkce:
            pkce_pair = generate_pkce_pair()
            code_verifier = pkce_pair.code_verifier
            code_challenge = pkce_pair.code_challenge
            code_challenge_method = pkce_pair.code_challenge_method
            extra_kwargs["code_challenge"] = code_challenge
            extra_kwargs["code_challenge_method"] = code_challenge_method

        nonce: str | None = None
        if use_nonce:
            nonce = generate_oidc_nonce()
            extra_kwargs["nonce"] = nonce

        auth_url = self.get_authorization_url(
            state=resolved_state,
            redirect_uri=redirect_uri,
            **extra_kwargs,
        )
        return OAuthAuthorizationRequest(
            url=auth_url,
            state=resolved_state,
            code_verifier=code_verifier,
            code_challenge=code_challenge,
            code_challenge_method=code_challenge_method,
            nonce=nonce,
        )

    @abstractmethod
    async def exchange_code(
        self,
        code: str,
        redirect_uri: str,
        *,
        code_verifier: str | None = None,
        expected_nonce: str | None = None,
    ) -> OAuthUserInfo:
        """Exchange the provider's authorization code for normalized user claims.

        Args:
            code: Temporary authorization code returned by provider.
            redirect_uri: Same redirect URI used in authorization request.
            code_verifier: Optional RFC 7636 PKCE verifier matching prior challenge.
            expected_nonce: Optional OIDC nonce expected inside returned ID tokens.

        Returns:
            Normalized OAuthUserInfo containing email, provider ID, and claims.

        Raises:
            OAuthProviderError: If token exchange or user-info retrieval fails.
        """


__all__ = [
    "OAuthProviderPort",
    "TokenStorePort",
    "UserRepositoryPort",
]
