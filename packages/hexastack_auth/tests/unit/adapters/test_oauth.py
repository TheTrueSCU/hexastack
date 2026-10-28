from unittest.mock import AsyncMock, MagicMock, patch

import pytest

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
