import time
from datetime import timedelta

import pytest

from hexastack_auth.adapters.in_memory import (
    InMemoryPasswordHasher,
    InMemorySecurityService,
)
from hexastack_auth.domain.exceptions import (
    InvalidTokenError,
    TokenExpiredError,
)
from hexastack_auth.domain.models import Identity


def test_in_memory_password_hasher():
    hasher = InMemoryPasswordHasher()
    hashed = hasher.hash_password("secret")
    assert hashed == "mock_hash:secret"
    assert hasher.verify_password("secret", hashed) is True
    assert hasher.verify_password("wrong", hashed) is False
    assert hasher.verify_password("secret", "mock_hash:other") is False


def test_in_memory_security_service_creation_and_lookup(
    sample_identity: Identity,
):
    svc = InMemorySecurityService(default_ttl_seconds=3600)
    token = svc.create_token(sample_identity)
    assert isinstance(token, str)
    assert token.startswith("mem_token_")

    # Internal table verification (killing arithmetic and assignment mutants)
    assert token in svc._tokens
    stored_ident, exp_time = svc._tokens[token]
    assert stored_ident == sample_identity
    assert exp_time is not None
    assert exp_time > time.time()
    assert abs((exp_time - time.time()) - 3600) < 5

    # Verification
    decoded = svc.verify_token(token)
    assert decoded.user_id == sample_identity.user_id
    assert decoded.roles == sample_identity.roles

    # Clear
    svc.clear()
    assert len(svc._tokens) == 0
    with pytest.raises(InvalidTokenError, match="not recognized"):
        svc.verify_token(token)


def test_in_memory_security_service_custom_ttls(sample_identity: Identity):
    svc = InMemorySecurityService(default_ttl_seconds=7200)

    # Timedelta TTL
    token_td = svc.create_token(sample_identity, ttl=timedelta(minutes=10))
    _, exp_td = svc._tokens[token_td]
    assert exp_td is not None
    assert abs((exp_td - time.time()) - 600) < 5

    # Integer TTL
    token_int = svc.create_token(sample_identity, ttl=1800)
    _, exp_int = svc._tokens[token_int]
    assert exp_int is not None
    assert abs((exp_int - time.time()) - 1800) < 5


def test_in_memory_security_service_default_constructor():
    svc = InMemorySecurityService()
    assert svc._default_ttl_seconds == 3600
    assert svc._tokens == {}


def test_in_memory_security_service_expiration(sample_identity: Identity):
    svc = InMemorySecurityService(default_ttl_seconds=3600)
    # Expired token with negative ttl
    token = svc.create_token(sample_identity, ttl=-10)
    assert token in svc._tokens

    with pytest.raises(TokenExpiredError, match="has expired"):
        svc.verify_token(token)

    # Expired token is removed on verification attempt
    assert token not in svc._tokens


def test_in_memory_security_service_invalid_and_empty_tokens(
    sample_identity: Identity,
):
    svc = InMemorySecurityService()
    with pytest.raises(InvalidTokenError, match="not recognized"):
        svc.verify_token("")

    with pytest.raises(InvalidTokenError, match="not recognized"):
        svc.verify_token("unknown_non_existent_token")
