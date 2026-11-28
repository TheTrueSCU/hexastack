"""Unit tests for pure OAuth2 PKCE and OIDC domain primitives."""

import pytest

from hexastack_auth.domain.oidc import (
    DEFAULT_ASYMMETRIC_OIDC_ALGORITHMS,
    FORBIDDEN_OIDC_ALGORITHMS,
    OAuthAuthorizationRequest,
    OidcDiscoveryDocument,
    OidcTokenPolicy,
    compute_pkce_s256_challenge,
    generate_oidc_nonce,
    generate_pkce_pair,
    verify_pkce_s256,
)


def test_pkce_rfc7636_appendix_b_vector() -> None:
    """Verify compute_pkce_s256_challenge matches RFC 7636 Appendix B vector."""
    verifier = "dBjftJeZ4CVP-mB92K27uhbUJU1p1r_wW1gFWFOEjXk"  # pragma: allowlist secret
    expected_challenge = (
        "E9Melhoa2OwvFrEMTJguCHaoeK1t8URWbuGJSstw-cM"  # pragma: allowlist secret
    )
    challenge = compute_pkce_s256_challenge(verifier)
    assert challenge == expected_challenge
    verified = verify_pkce_s256(verifier, expected_challenge)
    assert verified is True
    mismatch = verify_pkce_s256(verifier, "wrong-challenge")
    assert mismatch is False


def test_pkce_verifier_validation_and_generation() -> None:
    """Verify PKCE generation bounds and syntax validation."""
    with pytest.raises(ValueError, match="between 43 and 128"):
        generate_pkce_pair(length=42)
    with pytest.raises(ValueError, match="between 43 and 128"):
        generate_pkce_pair(length=129)

    pair = generate_pkce_pair(length=64)
    verifier_len = len(pair.code_verifier)
    assert verifier_len == 64
    method = pair.code_challenge_method
    assert method == "S256"
    ok = verify_pkce_s256(pair.code_verifier, pair.code_challenge)
    assert ok is True

    with pytest.raises(ValueError, match="43..128"):
        compute_pkce_s256_challenge("too-short")
    with pytest.raises(ValueError, match="RFC 7636"):
        compute_pkce_s256_challenge("a" * 42 + "+")

    bad_verify = verify_pkce_s256("invalid", pair.code_challenge)
    assert bad_verify is False
    empty_challenge_verify = verify_pkce_s256(pair.code_verifier, "")
    assert empty_challenge_verify is False


def test_oidc_nonce_and_auth_request() -> None:
    """Verify CSPRNG OIDC nonce generation and OAuthAuthorizationRequest container."""
    with pytest.raises(ValueError, match="at least 16"):
        generate_oidc_nonce(nbytes=8)

    nonce_a = generate_oidc_nonce()
    nonce_b = generate_oidc_nonce()
    assert len(nonce_a) >= 32
    assert nonce_a != nonce_b

    req = OAuthAuthorizationRequest(
        url="https://idp.example.com/authorize?state=s1",
        state="s1",
        code_verifier="v" * 43,
        code_challenge="c",
        code_challenge_method="S256",
        nonce=nonce_a,
    )
    assert req.state == "s1"
    assert req.nonce == nonce_a


def test_oidc_discovery_document_parsing() -> None:
    """Verify OidcDiscoveryDocument.from_dict validation and optional fields."""
    doc = OidcDiscoveryDocument.from_dict(
        {
            "issuer": "https://idp.example.com/realms/main",
            "authorization_endpoint": "https://idp.example.com/auth",
            "token_endpoint": "https://idp.example.com/token",
            "jwks_uri": "https://idp.example.com/jwks.json",
            "userinfo_endpoint": "https://idp.example.com/userinfo",
            "end_session_endpoint": " ",
            "id_token_signing_alg_values_supported": ["RS256", "EdDSA"],
            "code_challenge_methods_supported": ["S256"],
        }
    )
    assert doc.issuer == "https://idp.example.com/realms/main"
    assert doc.userinfo_endpoint == "https://idp.example.com/userinfo"
    assert doc.end_session_endpoint is None
    assert doc.id_token_signing_alg_values_supported == ("RS256", "EdDSA")
    assert doc.code_challenge_methods_supported == ("S256",)

    with pytest.raises(ValueError, match="jwks_uri"):
        OidcDiscoveryDocument.from_dict(
            {
                "issuer": "https://idp.example.com",
                "authorization_endpoint": "https://idp.example.com/auth",
                "token_endpoint": "https://idp.example.com/token",
            }
        )


def test_oidc_token_policy_rejects_symmetric_and_none_algorithms() -> None:
    """Verify OidcTokenPolicy forbids HS* symmetric algorithms, 'none', and empty fields."""
    assert "RS256" in DEFAULT_ASYMMETRIC_OIDC_ALGORITHMS
    assert "none" in FORBIDDEN_OIDC_ALGORITHMS

    policy = OidcTokenPolicy(
        issuer="https://idp.example.com",
        audience=("api-1", "api-2"),
    )
    assert policy.issuer == "https://idp.example.com"
    assert policy.audience == ("api-1", "api-2")

    for bad_alg in ("HS256", "HS384", "HS512", "none", "NONE", ""):
        with pytest.raises(ValueError):
            OidcTokenPolicy(
                issuer="https://idp.example.com",
                audience="api-1",
                allowed_algorithms=(bad_alg,),
            )

    with pytest.raises(ValueError, match="allowed_algorithms"):
        OidcTokenPolicy(
            issuer="https://idp.example.com",
            audience="api-1",
            allowed_algorithms=(),
        )
    with pytest.raises(ValueError, match="issuer"):
        OidcTokenPolicy(issuer="", audience="api-1")
    with pytest.raises(ValueError, match="audience"):
        OidcTokenPolicy(issuer="https://idp.example.com", audience=" ")
    with pytest.raises(ValueError, match="audience"):
        OidcTokenPolicy(issuer="https://idp.example.com", audience=("ok", ""))
    with pytest.raises(ValueError, match="leeway_seconds"):
        OidcTokenPolicy(
            issuer="https://idp.example.com",
            audience="api-1",
            leeway_seconds=-1,
        )
