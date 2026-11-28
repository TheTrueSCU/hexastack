"""OAuth2 and OpenID Connect identity provider adapters.

Notes/Architectural Intent:
    Provides concrete implementations of OAuthProviderPort for Google, GitHub,
    and Generic OIDC identity providers, standardizing token exchange and user claims.
"""

from __future__ import annotations

import hmac
import urllib.parse
from collections.abc import Mapping
from typing import Any, Self

import jwt

from hexastack_auth.adapters.oidc import (
    JwksOidcSecurityAdapter,
    discover_oidc_configuration,
    discover_oidc_configuration_async,
)
from hexastack_auth.domain.exceptions import InvalidTokenError, OAuthProviderError
from hexastack_auth.domain.oidc import DEFAULT_ASYMMETRIC_OIDC_ALGORITHMS
from hexastack_auth.domain.user import OAuthUserInfo
from hexastack_auth.ports.user import OAuthProviderPort
from hexastack_core.utils.imports import require_dependency


def _require_httpx() -> Any:
    return require_dependency(
        "httpx",
        extra="oidc",
        package="hexastack-auth",
        feature_name="OAuth identity provider",
    )


def _validate_pkce_method(code_challenge_method: str | None) -> str:
    """Validate that PKCE challenge method strictly uses S256."""
    resolved = "S256" if code_challenge_method is None else code_challenge_method
    if resolved != "S256":
        msg = (
            f"Unsupported PKCE code_challenge_method '{resolved}'; "
            "only 'S256' is permitted."
        )
        raise ValueError(msg)
    return resolved


class BaseOAuthProvider(OAuthProviderPort):
    """Base class for OAuth2 Authorization Code Grant providers.

    Notes/Architectural Intent:
        Encapsulates standard OAuth2 redirect generation, PKCE ``S256``, OIDC
        ``nonce`` validation, and HTTP token/userinfo exchange logic using httpx
        without vendor lock-in.
    """

    def __init__(
        self,
        client_id: str,
        client_secret: str | None = None,
        authorize_url: str = "",
        token_url: str = "",
        userinfo_url: str = "",
        scopes: tuple[str, ...] = (),
        name: str = "oauth",
        *,
        http_client: Any | None = None,
        id_token_verifier: Any | None = None,
    ) -> None:
        """Initialize BaseOAuthProvider.

        Args:
            client_id: OAuth client ID.
            client_secret: Optional OAuth client secret (omitted for public PKCE clients).
            authorize_url: Provider authorization endpoint.
            token_url: Provider token exchange endpoint.
            userinfo_url: Provider profile/userinfo endpoint.
            scopes: Sequence of requested OAuth scopes.
            name: Canonical provider name.
            http_client: Optional caller-managed async httpx client.
            id_token_verifier: Optional verifier implementing ``verify_id_token``.
        """
        self._client_id = client_id
        self._client_secret = client_secret
        self._authorize_url = authorize_url
        self._token_url = token_url
        self._userinfo_url = userinfo_url
        self._scopes = scopes
        self._name = name
        self._http_client = http_client
        self._id_token_verifier = id_token_verifier

    @property
    def name(self) -> str:
        """Provider name identifier."""
        return self._name

    def get_authorization_url(
        self,
        state: str,
        redirect_uri: str,
        *,
        code_challenge: str | None = None,
        code_challenge_method: str | None = None,
        nonce: str | None = None,
    ) -> str:
        """Build authorization redirect URL with state, scopes, PKCE S256, and nonce."""
        params: dict[str, str] = {
            "client_id": self._client_id,
            "redirect_uri": redirect_uri,
            "response_type": "code",
            "scope": " ".join(self._scopes),
            "state": state,
        }
        if code_challenge_method is not None or code_challenge is not None:
            method = _validate_pkce_method(code_challenge_method)
            if code_challenge is not None:
                params["code_challenge"] = code_challenge
                params["code_challenge_method"] = method
        if nonce is not None:
            params["nonce"] = nonce

        encoded = urllib.parse.urlencode(params)
        separator = "&" if "?" in self._authorize_url else "?"
        return f"{self._authorize_url}{separator}{encoded}"

    async def _http_post_token(self, data: dict[str, str]) -> dict[str, Any]:
        """Execute authorization_code POST against token endpoint."""
        headers = {"Accept": "application/json"}
        if self._http_client is not None:
            resp = await self._http_client.post(
                self._token_url, data=data, headers=headers
            )
        else:
            httpx = _require_httpx()
            async with httpx.AsyncClient() as client:
                resp = await client.post(self._token_url, data=data, headers=headers)

        if resp.status_code != 200:
            msg = f"Token exchange failed: {resp.status_code} {resp.text}"
            raise OAuthProviderError(self.name, msg)
        return resp.json()  # type: ignore[no-any-return]

    async def _fetch_userinfo(self, access_token: str) -> dict[str, Any]:
        """Fetch raw userinfo dictionary using bearer access token."""
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Accept": "application/json",
        }
        if self._http_client is not None:
            resp = await self._http_client.get(self._userinfo_url, headers=headers)
        else:
            httpx = _require_httpx()
            async with httpx.AsyncClient() as client:
                resp = await client.get(self._userinfo_url, headers=headers)

        if resp.status_code != 200:
            msg = f"Failed to fetch userinfo from '{self.name}': {resp.status_code} {resp.text}"
            raise OAuthProviderError(self.name, msg)
        return resp.json()  # type: ignore[no-any-return]

    def _verify_id_token_payload(
        self,
        token_data: Mapping[str, Any],
        expected_nonce: str | None,
    ) -> dict[str, Any] | None:
        """Verify returned OIDC ``id_token`` signature and/or nonce when present."""
        raw_id_token = token_data.get("id_token")
        if not raw_id_token:
            return None
        if not isinstance(raw_id_token, str):
            msg = f"Invalid id_token payload type returned by '{self.name}'."
            raise OAuthProviderError(self.name, msg)

        if self._id_token_verifier is not None:
            try:
                verified: dict[str, Any] = self._id_token_verifier.verify_id_token(
                    raw_id_token,
                    expected_nonce=expected_nonce,
                    client_id=self._client_id,
                )
            except InvalidTokenError as exc:
                raise OAuthProviderError(self.name, str(exc)) from exc
            return verified

        if expected_nonce is not None:
            try:
                claims = jwt.decode(
                    raw_id_token,
                    options={"verify_signature": False},
                )
            except jwt.PyJWTError as exc:
                msg = f"Malformed id_token returned by '{self.name}': {exc}"
                raise OAuthProviderError(self.name, msg) from exc
            actual_nonce = claims.get("nonce")
            if not isinstance(actual_nonce, str) or not hmac.compare_digest(
                actual_nonce, expected_nonce
            ):
                msg = f"OIDC id_token nonce verification failed for '{self.name}'."
                raise OAuthProviderError(self.name, msg)
        return None

    async def exchange_code(
        self,
        code: str,
        redirect_uri: str,
        *,
        code_verifier: str | None = None,
        expected_nonce: str | None = None,
    ) -> OAuthUserInfo:
        """Exchange authorization code for tokens and extract normalized profile."""
        data: dict[str, str] = {
            "client_id": self._client_id,
            "code": code,
            "grant_type": "authorization_code",
            "redirect_uri": redirect_uri,
        }
        if self._client_secret:
            data["client_secret"] = self._client_secret
        if code_verifier is not None:
            data["code_verifier"] = code_verifier

        token_data = await self._http_post_token(data)
        verified_id_claims = self._verify_id_token_payload(token_data, expected_nonce)

        access_token = token_data.get("access_token")
        if not access_token:
            if verified_id_claims is not None and not self._userinfo_url:
                return self._normalize_user_info(verified_id_claims)
            msg = f"No access_token returned by '{self.name}'"
            raise OAuthProviderError(self.name, msg)

        if self._userinfo_url:
            raw_info = await self._fetch_userinfo(str(access_token))
            if verified_id_claims is not None:
                raw_info = {**verified_id_claims, **raw_info}
            return self._normalize_user_info(raw_info)

        if verified_id_claims is not None:
            return self._normalize_user_info(verified_id_claims)

        msg = f"No userinfo_url configured for '{self.name}' and no verified id_token."
        raise OAuthProviderError(self.name, msg)

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
        client_secret: str | None = None,
        scopes: tuple[str, ...] = ("openid", "email", "profile"),
        *,
        http_client: Any | None = None,
        id_token_verifier: Any | None = None,
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
            http_client=http_client,
            id_token_verifier=id_token_verifier,
        )


class GitHubOAuthProvider(BaseOAuthProvider):
    """GitHub OAuth2 identity provider."""

    def __init__(
        self,
        client_id: str,
        client_secret: str | None = None,
        scopes: tuple[str, ...] = ("read:user", "user:email"),
        *,
        http_client: Any | None = None,
        id_token_verifier: Any | None = None,
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
            http_client=http_client,
            id_token_verifier=id_token_verifier,
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
        client_secret: str | None = None,
        authorize_url: str = "",
        token_url: str = "",
        userinfo_url: str = "",
        scopes: tuple[str, ...] = ("openid", "email", "profile"),
        name: str = "oidc",
        *,
        http_client: Any | None = None,
        id_token_verifier: Any | None = None,
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
            http_client=http_client,
            id_token_verifier=id_token_verifier,
        )

    @classmethod
    def from_discovery(
        cls,
        discovery_url: str,
        *,
        client_id: str,
        client_secret: str | None = None,
        scopes: tuple[str, ...] = ("openid", "email", "profile"),
        name: str = "oidc",
        timeout: float = 5.0,
        discovery_http_client: Any | None = None,
        http_client: Any | None = None,
        allowed_algorithms: tuple[str, ...] = DEFAULT_ASYMMETRIC_OIDC_ALGORITHMS,
        jwk_client: Any | None = None,
    ) -> Self:
        """Discover OIDC endpoints and bind a ``JwksOidcSecurityAdapter`` verifier.

        Args:
            discovery_url: Issuer URL or explicit ``/.well-known/openid-configuration`` URL.
            client_id: OAuth2 client identifier.
            client_secret: Optional OAuth2 client secret (omit for PKCE public clients).
            scopes: Requested OIDC scopes.
            name: Canonical provider name identifier.
            timeout: Discovery/JWKS HTTP request timeout in seconds.
            discovery_http_client: Optional sync HTTP client for metadata fetch.
            http_client: Optional async HTTP client reused for token/userinfo calls.
            allowed_algorithms: Allowed asymmetric ID-token signature algorithms.
            jwk_client: Optional JWK client override.

        Returns:
            Configured ``GenericOidcProvider`` with verified JWKS ID-token validation.
        """
        doc = discover_oidc_configuration(
            discovery_url, timeout=timeout, http_client=discovery_http_client
        )
        verifier = JwksOidcSecurityAdapter(
            jwks_uri=doc.jwks_uri,
            issuer=doc.issuer,
            audience=client_id,
            allowed_algorithms=allowed_algorithms,
            jwks_timeout_seconds=timeout,
            jwk_client=jwk_client,
        )
        return cls(
            client_id=client_id,
            client_secret=client_secret,
            authorize_url=doc.authorization_endpoint,
            token_url=doc.token_endpoint,
            userinfo_url=doc.userinfo_endpoint or "",
            scopes=scopes,
            name=name,
            http_client=http_client,
            id_token_verifier=verifier,
        )

    @classmethod
    async def from_discovery_async(
        cls,
        discovery_url: str,
        *,
        client_id: str,
        client_secret: str | None = None,
        scopes: tuple[str, ...] = ("openid", "email", "profile"),
        name: str = "oidc",
        timeout: float = 5.0,
        http_client: Any | None = None,
        allowed_algorithms: tuple[str, ...] = DEFAULT_ASYMMETRIC_OIDC_ALGORITHMS,
        jwk_client: Any | None = None,
    ) -> Self:
        """Asynchronously discover OIDC endpoints and bind a JWKS ID-token verifier.

        Args:
            discovery_url: Issuer URL or explicit ``/.well-known/openid-configuration`` URL.
            client_id: OAuth2 client identifier.
            client_secret: Optional OAuth2 client secret (omit for PKCE public clients).
            scopes: Requested OIDC scopes.
            name: Canonical provider name identifier.
            timeout: Discovery/JWKS HTTP request timeout in seconds.
            http_client: Optional async HTTP client used for discovery and token calls.
            allowed_algorithms: Allowed asymmetric ID-token signature algorithms.
            jwk_client: Optional JWK client override.

        Returns:
            Configured ``GenericOidcProvider`` with verified JWKS ID-token validation.
        """
        doc = await discover_oidc_configuration_async(
            discovery_url, timeout=timeout, http_client=http_client
        )
        verifier = JwksOidcSecurityAdapter(
            jwks_uri=doc.jwks_uri,
            issuer=doc.issuer,
            audience=client_id,
            allowed_algorithms=allowed_algorithms,
            jwks_timeout_seconds=timeout,
            jwk_client=jwk_client,
        )
        return cls(
            client_id=client_id,
            client_secret=client_secret,
            authorize_url=doc.authorization_endpoint,
            token_url=doc.token_endpoint,
            userinfo_url=doc.userinfo_endpoint or "",
            scopes=scopes,
            name=name,
            http_client=http_client,
            id_token_verifier=verifier,
        )


__all__ = [
    "BaseOAuthProvider",
    "GenericOidcProvider",
    "GitHubOAuthProvider",
    "GoogleOAuthProvider",
]
