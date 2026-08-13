from datetime import timedelta

import pytest
from hexastack_auth.adapters.jwt import JwtSecurityAdapter
from hexastack_auth.domain.exceptions import (
    InvalidTokenError,
    TokenExpiredError,
)
from hexastack_auth.domain.models import Identity


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


def test_jwt_custom_ttl_expiration(sample_identity: Identity):
    adapter = JwtSecurityAdapter(
        secret_key="secret-key-1234567890-thirty-two-bytes-key",
        algorithm="HS256",
    )
    # Token with -1 second expiration (already expired)
    token = adapter.create_token(sample_identity, ttl=timedelta(seconds=-10))

    with pytest.raises(TokenExpiredError) as exc_info:
        adapter.verify_token(token)
    assert "expired" in str(exc_info.value).lower()


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


def test_jwt_empty_token(jwt_security: JwtSecurityAdapter):
    with pytest.raises(InvalidTokenError):
        jwt_security.verify_token("")
