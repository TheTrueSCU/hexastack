import jwt
import pytest

from hexastack_auth.adapters.jwt import JwtSecurityAdapter
from hexastack_auth.domain.exceptions import (
    InvalidTokenError,
)
from hexastack_auth.domain.models import Identity


def test_jwt_algorithm_mismatch(sample_identity: Identity):
    hs256_adapter = JwtSecurityAdapter(
        secret_key="secret-key-1234567890-thirty-two-bytes-key",
        algorithm="HS256",
    )
    hs512_adapter = JwtSecurityAdapter(
        secret_key="secret-key-1234567890-thirty-two-bytes-key",
        algorithm="HS512",
    )

    token_256 = hs256_adapter.create_token(sample_identity)
    with pytest.raises(InvalidTokenError):
        hs512_adapter.verify_token(token_256)


def test_jwt_creation_and_verification(
    jwt_security: JwtSecurityAdapter, sample_identity: Identity
):
    token = jwt_security.create_token(sample_identity)
    assert isinstance(token, str)

    decoded = jwt_security.verify_token(token)
    assert decoded.user_id == sample_identity.user_id
    assert decoded.roles == sample_identity.roles
    assert decoded.permissions == sample_identity.permissions
    assert decoded.tenant_id == sample_identity.tenant_id
    assert decoded.claims["email"] == "admin@hexastack.io"
    assert decoded.is_authenticated is True

    # Raw payload and header assertions (killing arithmetic, algorithm, and claim mutants)
    raw_payload = jwt.decode(token, options={"verify_signature": False})
    header = jwt.get_unverified_header(token)
    assert header["alg"] == "HS256"
    assert raw_payload["sub"] == sample_identity.user_id
    assert raw_payload["exp"] - raw_payload["iat"] == 3600
    assert raw_payload["roles"] == sorted(sample_identity.roles)
    assert raw_payload["permissions"] == sorted(sample_identity.permissions)


def test_jwt_custom_claims_and_no_tenant():
    adapter = JwtSecurityAdapter(
        secret_key="secret-key-1234567890-thirty-two-bytes-key"
    )
    ident = Identity(
        user_id="user_plain",
        roles=frozenset(["viewer"]),
        permissions=frozenset(),
        tenant_id=None,
        claims={"custom_flag": True, "sub": "should_not_override"},
    )
    token = adapter.create_token(ident)
    decoded = adapter.verify_token(token)
    assert decoded.user_id == "user_plain"
    assert decoded.tenant_id is None
    assert decoded.claims["custom_flag"] is True


def test_jwt_empty_and_malformed_tokens(jwt_security: JwtSecurityAdapter):
    with pytest.raises(InvalidTokenError, match="Token string cannot be empty"):
        jwt_security.verify_token("")

    with pytest.raises(InvalidTokenError):
        jwt_security.verify_token("not.a.valid.jwt")


def test_jwt_invalid_signature(
    jwt_security: JwtSecurityAdapter, sample_identity: Identity
):
    token = jwt_security.create_token(sample_identity)

    other_adapter = JwtSecurityAdapter(
        secret_key="different-secret-key-999-thirty-two-bytes-k",
        algorithm="HS256",
    )
    with pytest.raises(InvalidTokenError) as exc_info:
        other_adapter.verify_token(token)
    assert "invalid" in str(exc_info.value).lower()


def test_jwt_issuer_and_audience_claims(sample_identity: Identity):
    adapter = JwtSecurityAdapter(
        secret_key="secret-key-1234567890-thirty-two-bytes-key",
        issuer="https://auth.hexastack.io",
        audience="hexastack-api",
    )

    token = adapter.create_token(sample_identity)
    raw_payload = jwt.decode(token, options={"verify_signature": False})
    assert raw_payload["iss"] == "https://auth.hexastack.io"
    assert raw_payload["aud"] == "hexastack-api"

    # Verify successfully with matching adapter
    verified = adapter.verify_token(token)
    assert verified.user_id == sample_identity.user_id

    # Verify fails with mismatching issuer
    bad_iss_adapter = JwtSecurityAdapter(
        secret_key="secret-key-1234567890-thirty-two-bytes-key",
        issuer="https://other.domain.com",
        audience="hexastack-api",
    )
    with pytest.raises(InvalidTokenError):
        bad_iss_adapter.verify_token(token)

    # Verify fails with mismatching audience
    bad_aud_adapter = JwtSecurityAdapter(
        secret_key="secret-key-1234567890-thirty-two-bytes-key",
        issuer="https://auth.hexastack.io",
        audience="other-api",
    )
    with pytest.raises(InvalidTokenError):
        bad_aud_adapter.verify_token(token)


def test_jwt_missing_sub_claim():
    # Token manually crafted without sub claim
    raw_token = jwt.encode(
        {"roles": ["viewer"], "exp": 9999999999},
        "secret-key-1234567890-thirty-two-bytes-key",
        algorithm="HS256",
    )
    adapter = JwtSecurityAdapter(
        secret_key="secret-key-1234567890-thirty-two-bytes-key"
    )
    with pytest.raises(InvalidTokenError, match="missing required 'sub' claim"):
        adapter.verify_token(raw_token)


def test_jwt_ttl_variations_and_expiry(sample_identity: Identity):
    from datetime import timedelta

    from hexastack_auth.domain.exceptions import AuthError, TokenExpiredError

    adapter = JwtSecurityAdapter(
        secret_key="secret-key-1234567890-thirty-two-bytes-key",
        default_ttl_seconds=3600,
    )

    # 1. Custom integer ttl
    token_int = adapter.create_token(sample_identity, ttl=7200)
    payload_int = jwt.decode(token_int, options={"verify_signature": False})
    assert payload_int["exp"] - payload_int["iat"] == 7200

    # 2. Custom timedelta ttl
    token_td = adapter.create_token(sample_identity, ttl=timedelta(minutes=15))
    payload_td = jwt.decode(token_td, options={"verify_signature": False})
    assert payload_td["exp"] - payload_td["iat"] == 900

    # 3. Expired token raises TokenExpiredError
    token_expired = adapter.create_token(sample_identity, ttl=-10)
    with pytest.raises(TokenExpiredError, match="JWT token expired"):
        adapter.verify_token(token_expired)

    # 4. Signing failure raises AuthError
    bad_adapter = JwtSecurityAdapter(
        secret_key="secret-key-1234567890-thirty-two-bytes-key",
        algorithm="UNSUPPORTED_ALG",
    )
    with pytest.raises(AuthError, match="JWT signing failed"):
        bad_adapter.create_token(sample_identity)
