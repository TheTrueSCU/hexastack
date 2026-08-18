from datetime import timedelta

import jwt
import pytest

from hexastack_auth.adapters.jwt import JwtSecurityAdapter
from hexastack_auth.domain.exceptions import (
    InvalidTokenError,
    TokenExpiredError,
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
        claims={"plan": "enterprise", "sub": "should_not_overwrite"},
    )

    token = adapter.create_token(ident)
    raw = jwt.decode(token, options={"verify_signature": False})
    assert "tenant_id" not in raw
    assert raw["plan"] == "enterprise"
    assert raw["sub"] == "user_plain"  # standard sub is preserved

    verified = adapter.verify_token(token)
    assert verified.tenant_id is None
    assert verified.claims["plan"] == "enterprise"


def test_jwt_custom_int_and_duration_ttl(sample_identity: Identity):
    adapter = JwtSecurityAdapter(
        secret_key="secret-key-1234567890-thirty-two-bytes-key",
        algorithm="HS256",
        default_ttl_seconds=7200,
    )

    # Default TTL (7200)
    token_default = adapter.create_token(sample_identity)
    raw_def = jwt.decode(token_default, options={"verify_signature": False})
    assert raw_def["exp"] - raw_def["iat"] == 7200

    # Int TTL override (1800)
    token_int = adapter.create_token(sample_identity, ttl=1800)
    raw_int = jwt.decode(token_int, options={"verify_signature": False})
    assert raw_int["exp"] - raw_int["iat"] == 1800

    # Timedelta TTL override (300)
    token_delta = adapter.create_token(sample_identity, ttl=timedelta(minutes=5))
    raw_delta = jwt.decode(token_delta, options={"verify_signature": False})
    assert raw_delta["exp"] - raw_delta["iat"] == 300


def test_jwt_custom_ttl_expiration(sample_identity: Identity):
    adapter = JwtSecurityAdapter(
        secret_key="secret-key-1234567890-thirty-two-bytes-key",
        algorithm="HS256",
    )
    token = adapter.create_token(sample_identity, ttl=timedelta(seconds=-10))

    with pytest.raises(TokenExpiredError) as exc_info:
        adapter.verify_token(token)
    assert "expired" in str(exc_info.value).lower()


def test_jwt_default_constructor_parameters(sample_identity: Identity):
    adapter = JwtSecurityAdapter(secret_key="test-secret-key-1234567890-test-key")
    assert adapter._algorithm == "HS256"
    assert adapter._default_ttl.total_seconds() == 3600
    assert adapter._issuer is None
    assert adapter._audience is None

    token = adapter.create_token(sample_identity)
    headers = jwt.get_unverified_header(token)
    assert headers["alg"] == "HS256"
    raw_payload = jwt.decode(token, options={"verify_signature": False})
    assert raw_payload["exp"] - raw_payload["iat"] == 3600
    assert "iss" not in raw_payload
    assert "aud" not in raw_payload


def test_jwt_empty_and_malformed_tokens(jwt_security: JwtSecurityAdapter):
    with pytest.raises(InvalidTokenError):
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
