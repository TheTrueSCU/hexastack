from datetime import UTC, datetime, timedelta
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import jwt
import pytest
from cryptography.hazmat.primitives.asymmetric import rsa

from hexastack_auth.adapters.oauth import (
    BaseOAuthProvider,
    GenericOidcProvider,
    GitHubOAuthProvider,
    GoogleOAuthProvider,
)
from hexastack_auth.domain.exceptions import OAuthProviderError


def test_google_oauth_provider_url():
    provider = GoogleOAuthProvider(client_id="google-id", client_secret="google-secret")
    assert provider.name == "google"
    url = provider.get_authorization_url(
        state="state123", redirect_uri="http://localhost/cb"
    )
    assert "accounts.google.com" in url
    assert "client_id=google-id" in url
    assert "state=state123" in url
    assert "openid" in url


def test_github_oauth_provider_url():
    provider = GitHubOAuthProvider(client_id="github-id", client_secret="github-secret")
    assert provider.name == "github"
    url = provider.get_authorization_url(
        state="st456", redirect_uri="http://localhost/github/cb"
    )
    assert "github.com/login/oauth/authorize" in url
    assert "client_id=github-id" in url


def test_generic_oidc_provider_url():
    provider = GenericOidcProvider(
        client_id="keycloak-id",
        client_secret="keycloak-secret",  # pragma: allowlist secret
        authorize_url="https://auth.company.com/auth",
        token_url="https://auth.company.com/token",
        userinfo_url="https://auth.company.com/userinfo",
    )
    assert provider.name == "oidc"
    url = provider.get_authorization_url(
        state="oidc-state", redirect_uri="http://localhost/oidc/cb"
    )
    assert "https://auth.company.com/auth" in url


async def test_oauth_provider_exchange_code_success():
    provider = GoogleOAuthProvider(
        client_id="gid", client_secret="gsec"
    )  # pragma: allowlist secret

    mock_token_resp = MagicMock()
    mock_token_resp.status_code = 200
    mock_token_resp.json.return_value = {"access_token": "mock-access-token-123"}

    mock_user_resp = MagicMock()
    mock_user_resp.status_code = 200
    mock_user_resp.json.return_value = {
        "sub": "google-sub-456",
        "email": "googleuser@gmail.com",
        "name": "Google User",
        "picture": "https://lh3.googleusercontent.com/pic.jpg",
    }

    with patch("httpx.AsyncClient") as mock_client_cls:
        mock_client = AsyncMock()
        mock_client.post.return_value = mock_token_resp
        mock_client.get.return_value = mock_user_resp
        mock_client_cls.return_value.__aenter__.return_value = mock_client

        user_info = await provider.exchange_code("mock-code", "http://localhost/cb")
        assert user_info.provider == "google"
        assert user_info.account_id == "google-sub-456"
        assert user_info.email == "googleuser@gmail.com"
        assert user_info.name == "Google User"


async def test_oauth_provider_exchange_code_failure():
    provider = BaseOAuthProvider(
        client_id="id",
        client_secret="sec",  # pragma: allowlist secret
        authorize_url="https://auth",
        token_url="https://token",
        userinfo_url="https://user",
        scopes=("read",),
    )

    mock_token_resp = MagicMock()
    mock_token_resp.status_code = 400
    mock_token_resp.text = "invalid_grant"

    with patch("httpx.AsyncClient") as mock_client_cls:
        mock_client = AsyncMock()
        mock_client.post.return_value = mock_token_resp
        mock_client_cls.return_value.__aenter__.return_value = mock_client

        with pytest.raises(OAuthProviderError) as exc_info:
            await provider.exchange_code("bad-code", "http://localhost/cb")
        assert "Token exchange failed" in str(exc_info.value)


def test_oauth_provider_pkce_s256_rejects_plain() -> None:
    """Verify PKCE S256 parameters and rejection of plain code_challenge_method."""
    provider = GenericOidcProvider(
        client_id="public-cli",
        authorize_url="https://idp.example.com/authorize",
        token_url="https://idp.example.com/token",
        userinfo_url="https://idp.example.com/userinfo",
    )
    req = provider.create_authorization_request("http://127.0.0.1/cb", state="st-pkce")
    assert req.code_challenge is not None
    assert "code_challenge_method=S256" in req.url
    assert f"code_challenge={req.code_challenge}" in req.url
    assert f"nonce={req.nonce}" in req.url

    with pytest.raises(ValueError, match="only 'S256' is permitted"):
        provider.get_authorization_url(
            "st-bad",
            "http://127.0.0.1/cb",
            code_challenge="weak-plain",
            code_challenge_method="plain",
        )


async def test_public_client_exchange_code_with_pkce_and_discovery() -> None:
    """Verify public PKCE exchange omits client_secret, verifies ID token nonce, and supports discovery."""
    priv = rsa.generate_private_key(public_exponent=65537, key_size=2048)

    class _MockJwkClient:
        def get_jwk_set(self, *, refresh: bool = False) -> None:
            return

        def get_signing_key_from_jwt(self, token: str) -> SimpleNamespace:
            return SimpleNamespace(key=priv.public_key())

    now = datetime.now(UTC)
    id_token = jwt.encode(
        {
            "sub": "oidc-user-7",
            "iss": "https://idp.example.com",
            "aud": "public-cli",
            "nonce": "nonce-777",
            "email": "alice@example.com",
            "iat": int(now.timestamp()),
            "exp": int((now + timedelta(minutes=5)).timestamp()),
        },
        priv,
        algorithm="RS256",
        headers={"kid": "kid-1"},
    )

    discovery_resp = MagicMock()
    discovery_resp.status_code = 200
    discovery_resp.json.return_value = {
        "issuer": "https://idp.example.com",
        "authorization_endpoint": "https://idp.example.com/authorize",
        "token_endpoint": "https://idp.example.com/token",
        "jwks_uri": "https://idp.example.com/jwks.json",
    }
    sync_client = MagicMock()
    sync_client.get.return_value = discovery_resp

    token_resp = MagicMock()
    token_resp.status_code = 200
    token_resp.json.return_value = {
        "access_token": "acc-tok",
        "id_token": id_token,
    }
    async_client = AsyncMock()
    async_client.post.return_value = token_resp

    provider = GenericOidcProvider.from_discovery(
        "https://idp.example.com",
        client_id="public-cli",
        discovery_http_client=sync_client,
        http_client=async_client,
        jwk_client=_MockJwkClient(),
    )
    user_info = await provider.exchange_code(
        "code-ok",
        "http://127.0.0.1/cb",
        code_verifier="v" * 43,
        expected_nonce="nonce-777",
    )
    assert user_info.account_id == "oidc-user-7"
    assert user_info.email == "alice@example.com"
    posted_form = async_client.post.call_args.kwargs["data"]
    assert "client_secret" not in posted_form
    assert posted_form["code_verifier"] == "v" * 43

    with pytest.raises(OAuthProviderError, match="nonce"):
        await provider.exchange_code(
            "code-bad-nonce",
            "http://127.0.0.1/cb",
            code_verifier="v" * 43,
            expected_nonce="wrong-nonce",
        )

    async_client.get.return_value = discovery_resp
    async_provider = await GenericOidcProvider.from_discovery_async(
        "https://idp.example.com",
        client_id="public-cli",
        http_client=async_client,
        jwk_client=_MockJwkClient(),
    )
    assert async_provider.name == "oidc"
