"""Unit tests for JwksOidcSecurityAdapter and OIDC discovery adapters."""

from datetime import UTC, datetime, timedelta
from types import SimpleNamespace
from typing import Any
from unittest.mock import AsyncMock, MagicMock

import jwt
import pytest
from cryptography.hazmat.primitives.asymmetric import ec, ed25519, rsa

from hexastack_auth.adapters.oidc import (
    JwksOidcSecurityAdapter,
    discover_oidc_configuration,
    discover_oidc_configuration_async,
)
from hexastack_auth.domain.exceptions import (
    AuthError,
    InvalidTokenError,
    OAuthProviderError,
    TokenExpiredError,
)
from hexastack_auth.domain.models import Identity


def _sign_jwt(
    payload: dict[str, Any],
    key: Any,
    *,
    algorithm: str,
    kid: str = "kid-1",
    headers: dict[str, Any] | None = None,
) -> str:
    merged_headers = {"kid": kid, **(headers or {})}
    return jwt.encode(payload, key, algorithm=algorithm, headers=merged_headers)


def _base_claims(*, sub: str = "user-123", offset_seconds: int = 300) -> dict:
    now = datetime.now(UTC)
    return {
        "sub": sub,
        "iss": "https://idp.example.com",
        "aud": "hexastack-api",
        "iat": int(now.timestamp()),
        "exp": int((now + timedelta(seconds=offset_seconds)).timestamp()),
    }


def _make_key_client(public_keys_by_kid: dict[str, Any]) -> Any:
    class _StaticJwkClient:
        def __init__(self) -> None:
            self.keys = dict(public_keys_by_kid)
            self.refresh_calls = 0

        def get_jwk_set(self, *, refresh: bool = False) -> None:
            if refresh:
                self.refresh_calls += 1

        def get_signing_key_from_jwt(self, token: str) -> SimpleNamespace:
            header = jwt.get_unverified_header(token)
            kid = header.get("kid")
            if kid not in self.keys:
                raise jwt.PyJWKClientError(f"Unknown kid: {kid}")
            return SimpleNamespace(key=self.keys[kid])

    return _StaticJwkClient()


def test_jwks_adapter_verifies_rs256_es256_eddsa() -> None:
    """Verify RS256, ES256, and EdDSA asymmetric signatures and identity claim mapping."""
    rsa_priv = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    ec_priv = ec.generate_private_key(ec.SECP256R1())
    ed_priv = ed25519.Ed25519PrivateKey.generate()

    jwk_client = _make_key_client(
        {
            "rsa-1": rsa_priv.public_key(),
            "ec-1": ec_priv.public_key(),
            "ed-1": ed_priv.public_key(),
        }
    )
    adapter = JwksOidcSecurityAdapter(
        jwks_uri="https://idp.example.com/.well-known/jwks.json",
        issuer="https://idp.example.com",
        audience="hexastack-api",
        jwk_client=jwk_client,
    )

    for kid, priv, alg in (
        ("rsa-1", rsa_priv, "RS256"),
        ("ec-1", ec_priv, "ES256"),
        ("ed-1", ed_priv, "EdDSA"),
    ):
        claims = {
            **_base_claims(sub=f"sub-{alg}"),
            "roles": ["admin", "ops"],
            "permissions": "jobs:read jobs:write",
            "tenant_id": "tenant-42",
        }
        token = _sign_jwt(
            claims, priv, algorithm=alg, kid=kid, headers={"typ": "at+jwt"}
        )
        identity = adapter.verify_token(token)
        assert identity.user_id == f"sub-{alg}"
        assert identity.roles == frozenset({"admin", "ops"})
        assert identity.permissions == frozenset({"jobs:read", "jobs:write"})
        assert identity.tenant_id == "tenant-42"
        assert identity.is_authenticated is True


def test_jwks_adapter_retries_on_live_key_rotation() -> None:
    """Verify adapter refreshes JWKS once when encountering a newly rotated kid."""
    old_priv = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    new_priv = rsa.generate_private_key(public_exponent=65537, key_size=2048)

    class _RotatingJwkClient:
        def __init__(self) -> None:
            self.keys: dict[str, object] = {"kid-1": old_priv.public_key()}
            self.refresh_calls = 0

        def get_jwk_set(self, *, refresh: bool = False) -> None:
            if refresh:
                self.refresh_calls += 1
                self.keys["kid-2"] = new_priv.public_key()

        def get_signing_key_from_jwt(self, token: str) -> SimpleNamespace:
            kid = jwt.get_unverified_header(token).get("kid")
            if kid not in self.keys:
                raise jwt.PyJWKClientError(f"Unknown kid: {kid}")
            return SimpleNamespace(key=self.keys[kid])

    jwk_client = _RotatingJwkClient()
    adapter = JwksOidcSecurityAdapter(
        jwks_uri="https://idp.example.com/jwks.json",
        issuer="https://idp.example.com",
        audience="hexastack-api",
        jwk_client=jwk_client,
    )

    rotated_token = _sign_jwt(_base_claims(), new_priv, algorithm="RS256", kid="kid-2")
    identity = adapter.verify_token(rotated_token)
    assert identity.user_id == "user-123"
    refresh_count = jwk_client.refresh_calls
    assert refresh_count == 1

    unknown_token = _sign_jwt(_base_claims(), new_priv, algorithm="RS256", kid="kid-9")
    with pytest.raises(InvalidTokenError, match="Unable to resolve OIDC signing key"):
        adapter.verify_token(unknown_token)


def test_jwks_adapter_rejects_id_tokens_and_enforces_at_jwt() -> None:
    """Verify resource-server verification rejects ID tokens and enforces optional typ=at+jwt."""
    priv = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    jwk_client = _make_key_client({"kid-1": priv.public_key()})

    adapter = JwksOidcSecurityAdapter(
        jwks_uri="https://idp.example.com/jwks.json",
        issuer="https://idp.example.com",
        audience="hexastack-api",
        jwk_client=jwk_client,
    )

    id_token_use = _sign_jwt(
        {**_base_claims(), "token_use": "id"}, priv, algorithm="RS256"
    )
    with pytest.raises(InvalidTokenError, match="token_use=id"):
        adapter.verify_token(id_token_use)

    for marker in ("nonce", "at_hash", "c_hash"):
        tok = _sign_jwt({**_base_claims(), marker: "val"}, priv, algorithm="RS256")
        with pytest.raises(InvalidTokenError, match=marker):
            adapter.verify_token(tok)

    id_typ_tok = _sign_jwt(
        _base_claims(), priv, algorithm="RS256", headers={"typ": "id+jwt"}
    )
    with pytest.raises(InvalidTokenError, match="typ=id\\+jwt"):
        adapter.verify_token(id_typ_tok)

    strict_adapter = JwksOidcSecurityAdapter(
        jwks_uri="https://idp.example.com/jwks.json",
        issuer="https://idp.example.com",
        audience="hexastack-api",
        require_access_token_typ=True,
        jwk_client=jwk_client,
    )
    plain_access = _sign_jwt(_base_claims(), priv, algorithm="RS256")
    with pytest.raises(InvalidTokenError, match="at\\+jwt"):
        strict_adapter.verify_token(plain_access)

    rfc9068_access = _sign_jwt(
        _base_claims(),
        priv,
        algorithm="RS256",
        headers={"typ": "application/at+jwt"},
    )
    verified = strict_adapter.verify_token(rfc9068_access)
    assert verified.user_id == "user-123"


def test_jwks_adapter_rejects_expired_wrong_claims_alg_confusion_and_minting() -> None:
    """Verify expiration, issuer/audience mismatch, sub check, alg=none/HS256, and mint block."""
    priv = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    jwk_client = _make_key_client({"kid-1": priv.public_key()})

    adapter = JwksOidcSecurityAdapter(
        jwks_uri="https://idp.example.com/jwks.json",
        issuer="https://idp.example.com",
        audience="hexastack-api",
        leeway_seconds=0,
        jwk_client=jwk_client,
    )

    with pytest.raises(AuthError, match="verification-only"):
        adapter.create_token(Identity(user_id="alice"))

    with pytest.raises(InvalidTokenError, match="cannot be empty"):
        adapter.verify_token("")

    with pytest.raises(ValueError, match="http://' or 'https://'"):
        JwksOidcSecurityAdapter(
            jwks_uri="file:///etc/passwd",
            issuer="https://idp.example.com",
            audience="hexastack-api",
        )

    expired_tok = _sign_jwt(_base_claims(offset_seconds=-10), priv, algorithm="RS256")
    with pytest.raises(TokenExpiredError):
        adapter.verify_token(expired_tok)

    wrong_iss = _sign_jwt(
        {**_base_claims(), "iss": "https://evil.example.com"},
        priv,
        algorithm="RS256",
    )
    with pytest.raises(InvalidTokenError):
        adapter.verify_token(wrong_iss)

    wrong_aud = _sign_jwt(
        {**_base_claims(), "aud": "wrong-api"},
        priv,
        algorithm="RS256",
    )
    with pytest.raises(InvalidTokenError):
        adapter.verify_token(wrong_aud)

    missing_sub = _sign_jwt({**_base_claims(), "sub": "  "}, priv, algorithm="RS256")
    with pytest.raises(InvalidTokenError, match="sub"):
        adapter.verify_token(missing_sub)

    hs_token = jwt.encode(_base_claims(), "hmac-secret-key-32-bytes-minimum!", "HS256")
    with pytest.raises(InvalidTokenError, match="forbidden"):
        adapter.verify_token(hs_token)

    alg_none_token = "eyJhbGciOiJub25lIiwidHlwIjoiSldUIn0.eyJzdWIiOiJhIn0."  # pragma: allowlist secret
    with pytest.raises(InvalidTokenError, match="forbidden"):
        adapter.verify_token(alg_none_token)


def test_jwks_adapter_verify_id_token_and_nonce() -> None:
    """Verify OIDC ID token verification validates signature, client_id aud, and nonce."""
    priv = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    jwk_client = _make_key_client({"kid-1": priv.public_key()})
    adapter = JwksOidcSecurityAdapter(
        jwks_uri="https://idp.example.com/jwks.json",
        issuer="https://idp.example.com",
        audience="client-abc",
        jwk_client=jwk_client,
    )

    id_token = _sign_jwt(
        {**_base_claims(), "aud": "client-abc", "nonce": "nonce-123"},
        priv,
        algorithm="RS256",
    )
    claims = adapter.verify_id_token(
        id_token, expected_nonce="nonce-123", client_id="client-abc"
    )
    assert claims["sub"] == "user-123"

    with pytest.raises(InvalidTokenError, match="nonce"):
        adapter.verify_id_token(
            id_token, expected_nonce="wrong-nonce", client_id="client-abc"
        )


def test_discovery_sync_and_async_construct_adapter() -> None:
    """Verify OIDC discovery helpers and from_discovery / from_discovery_async."""
    meta = {
        "issuer": "https://idp.example.com",
        "authorization_endpoint": "https://idp.example.com/authorize",
        "token_endpoint": "https://idp.example.com/token",
        "jwks_uri": "https://idp.example.com/jwks.json",
        "userinfo_endpoint": "https://idp.example.com/userinfo",
    }
    resp = MagicMock()
    resp.status_code = 200
    resp.json.return_value = meta

    sync_client = MagicMock()
    sync_client.get.return_value = resp
    doc = discover_oidc_configuration(
        "https://idp.example.com", http_client=sync_client
    )
    assert doc.jwks_uri == "https://idp.example.com/jwks.json"
    called_url = sync_client.get.call_args[0][0]
    assert called_url == "https://idp.example.com/.well-known/openid-configuration"

    priv = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    jwk_client = _make_key_client({"kid-1": priv.public_key()})
    adapter = JwksOidcSecurityAdapter.from_discovery(
        "https://idp.example.com/.well-known/openid-configuration",
        audience="hexastack-api",
        http_client=sync_client,
        jwk_client=jwk_client,
    )
    tok = _sign_jwt(_base_claims(), priv, algorithm="RS256")
    ident = adapter.verify_token(tok)
    assert ident.user_id == "user-123"

    bad_resp = MagicMock()
    bad_resp.status_code = 502
    bad_resp.text = "Bad Gateway"
    sync_client.get.return_value = bad_resp
    with pytest.raises(OAuthProviderError, match="502"):
        discover_oidc_configuration("https://idp.example.com", http_client=sync_client)

    with pytest.raises(ValueError, match="http://' or 'https://'"):
        discover_oidc_configuration("file:///etc/passwd")


async def test_discovery_async_and_from_discovery_async() -> None:
    """Verify async OIDC discovery and adapter construction."""
    meta = {
        "issuer": "https://idp.example.com",
        "authorization_endpoint": "https://idp.example.com/authorize",
        "token_endpoint": "https://idp.example.com/token",
        "jwks_uri": "https://idp.example.com/jwks.json",
    }
    resp = MagicMock()
    resp.status_code = 200
    resp.json.return_value = meta

    async_client = AsyncMock()
    async_client.get.return_value = resp
    doc = await discover_oidc_configuration_async(
        "https://idp.example.com", http_client=async_client
    )
    assert doc.token_endpoint == "https://idp.example.com/token"

    priv = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    jwk_client = _make_key_client({"kid-1": priv.public_key()})
    adapter = await JwksOidcSecurityAdapter.from_discovery_async(
        "https://idp.example.com",
        audience="hexastack-api",
        http_client=async_client,
        jwk_client=jwk_client,
    )
    tok = _sign_jwt(_base_claims(), priv, algorithm="RS256")
    ident = adapter.verify_token(tok)
    assert ident.user_id == "user-123"
