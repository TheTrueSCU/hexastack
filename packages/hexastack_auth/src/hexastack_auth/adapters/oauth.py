"""OAuth2 and OpenID Connect identity provider adapters.

Notes/Architectural Intent:
    Provides concrete implementations of OAuthProviderPort for Google, GitHub,
    and Generic OIDC identity providers, standardizing token exchange and user claims.
"""

from __future__ import annotations

import urllib.parse
from typing import Any

from hexastack_auth.domain.exceptions import OAuthProviderError
from hexastack_auth.domain.user import OAuthUserInfo
from hexastack_auth.ports.user import OAuthProviderPort
from hexastack_core.utils.imports import require_dependency


def _require_httpx() -> Any:
    return require_dependency(
        "httpx",
        extra="all",
        package="hexastack-auth",
        feature_name="OAuth identity provider",
    )


class BaseOAuthProvider(OAuthProviderPort):
    """Base class for OAuth2 Authorization Code Grant providers.

    Notes/Architectural Intent:
        Encapsulates standard OAuth2 redirect generation and HTTP token/userinfo
        exchange logic using httpx without vendor lock-in.
    """

    def __init__(
        self,
        client_id: str,
        client_secret: str,
        authorize_url: str,
        token_url: str,
        userinfo_url: str,
        scopes: tuple[str, ...],
        name: str = "oauth",
    ) -> None:
        """Initialize BaseOAuthProvider.

        Args:
            client_id: OAuth client ID.
            client_secret: OAuth client secret.
            authorize_url: Provider authorization endpoint.
            token_url: Provider token exchange endpoint.
            userinfo_url: Provider profile/userinfo endpoint.
            scopes: Sequence of requested OAuth scopes.
            name: Canonical provider name.
        """
        self._client_id = client_id
        self._client_secret = client_secret
        self._authorize_url = authorize_url
        self._token_url = token_url
        self._userinfo_url = userinfo_url
        self._scopes = scopes
        self._name = name

    @property
    def name(self) -> str:
        """Provider name identifier."""
        return self._name

    def get_authorization_url(self, state: str, redirect_uri: str) -> str:
        """Build the authorization redirect URL with state and scopes."""
        params = {
            "client_id": self._client_id,
            "redirect_uri": redirect_uri,
            "response_type": "code",
            "scope": " ".join(self._scopes),
            "state": state,
        }
        encoded = urllib.parse.urlencode(params)
        separator = "&" if "?" in self._authorize_url else "?"
        return f"{self._authorize_url}{separator}{encoded}"

    async def _fetch_userinfo(self, access_token: str) -> dict[str, Any]:
        """Fetch raw userinfo dictionary using bearer access token."""
        httpx = _require_httpx()

        headers = {
            "Authorization": f"Bearer {access_token}",
            "Accept": "application/json",
        }
        async with httpx.AsyncClient() as client:
            resp = await client.get(self._userinfo_url, headers=headers)
            if resp.status_code != 200:
                msg = f"Failed to fetch userinfo from '{self.name}': {resp.status_code} {resp.text}"
                raise OAuthProviderError(self.name, msg)
            return resp.json()  # type: ignore[no-any-return]

    async def exchange_code(self, code: str, redirect_uri: str) -> OAuthUserInfo:
        """Exchange authorization code for tokens and extract normalized profile."""
        httpx = _require_httpx()

        data = {
            "client_id": self._client_id,
            "client_secret": self._client_secret,
            "code": code,
            "grant_type": "authorization_code",
            "redirect_uri": redirect_uri,
        }
        headers = {"Accept": "application/json"}

        async with httpx.AsyncClient() as client:
            resp = await client.post(self._token_url, data=data, headers=headers)
            if resp.status_code != 200:
                msg = f"Token exchange failed: {resp.status_code} {resp.text}"
                raise OAuthProviderError(self.name, msg)

            token_data = resp.json()
            access_token = token_data.get("access_token")
            if not access_token:
                msg = f"No access_token returned by '{self.name}'"
                raise OAuthProviderError(self.name, msg)

        raw_info = await self._fetch_userinfo(access_token)
        return self._normalize_user_info(raw_info)

    def _normalize_user_info(self, raw_info: dict[str, Any]) -> OAuthUserInfo:
        """Convert raw provider userinfo dictionary into standard OAuthUserInfo."""
        account_id = str(raw_info.get("sub") or raw_info.get("id", ""))
        email = str(raw_info.get("email", ""))
        name = raw_info.get("name")
        avatar = raw_info.get("picture") or raw_info.get("avatar_url")
        return OAuthUserInfo(
            provider=self.name,
            account_id=account_id,
            email=email,
            name=name,
            avatar_url=avatar,
            claims=raw_info,
        )


class GoogleOAuthProvider(BaseOAuthProvider):
    """Google OAuth2 and OpenID Connect identity provider."""

    def __init__(
        self,
        client_id: str,
        client_secret: str,
        scopes: tuple[str, ...] = ("openid", "email", "profile"),
    ) -> None:
        """Initialize Google OAuth provider."""
        super().__init__(
            client_id=client_id,
            client_secret=client_secret,
            authorize_url="https://accounts.google.com/o/oauth2/v2/auth",
            token_url="https://oauth2.googleapis.com/token",
            userinfo_url="https://www.googleapis.com/oauth2/v3/userinfo",
            scopes=scopes,
            name="google",
        )


class GitHubOAuthProvider(BaseOAuthProvider):
    """GitHub OAuth2 identity provider."""

    def __init__(
        self,
        client_id: str,
        client_secret: str,
        scopes: tuple[str, ...] = ("read:user", "user:email"),
    ) -> None:
        """Initialize GitHub OAuth provider."""
        super().__init__(
            client_id=client_id,
            client_secret=client_secret,
            authorize_url="https://github.com/login/oauth/authorize",
            token_url="https://github.com/login/oauth/access_token",
            userinfo_url="https://api.github.com/user",
            scopes=scopes,
            name="github",
        )

    def _normalize_user_info(self, raw_info: dict[str, Any]) -> OAuthUserInfo:
        """Normalize GitHub profile info."""
        account_id = str(raw_info.get("id", ""))
        email = str(
            raw_info.get("email") or f"{raw_info.get('login', 'user')}@github.user"
        )
        name = raw_info.get("name") or raw_info.get("login")
        avatar = raw_info.get("avatar_url")
        return OAuthUserInfo(
            provider=self.name,
            account_id=account_id,
            email=email,
            name=name,
            avatar_url=avatar,
            claims=raw_info,
        )


class GenericOidcProvider(BaseOAuthProvider):
    """Generic OpenID Connect (OIDC) identity provider with configurable endpoints."""

    def __init__(
        self,
        client_id: str,
        client_secret: str,
        authorize_url: str,
        token_url: str,
        userinfo_url: str,
        scopes: tuple[str, ...] = ("openid", "email", "profile"),
        name: str = "oidc",
    ) -> None:
        """Initialize generic OIDC provider with custom endpoint URLs."""
        super().__init__(
            client_id=client_id,
            client_secret=client_secret,
            authorize_url=authorize_url,
            token_url=token_url,
            userinfo_url=userinfo_url,
            scopes=scopes,
            name=name,
        )


__all__ = [
    "BaseOAuthProvider",
    "GenericOidcProvider",
    "GitHubOAuthProvider",
    "GoogleOAuthProvider",
]
