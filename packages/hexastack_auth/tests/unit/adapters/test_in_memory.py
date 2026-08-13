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


def test_in_memory_security_service(sample_identity: Identity):
    svc = InMemorySecurityService(default_ttl_seconds=3600)
    token = svc.create_token(sample_identity)
    assert isinstance(token, str)

    decoded = svc.verify_token(token)
    assert decoded.user_id == sample_identity.user_id
    assert decoded.roles == sample_identity.roles

    svc.clear()
    with pytest.raises(InvalidTokenError):
        svc.verify_token(token)


def test_in_memory_security_service_expiration(sample_identity: Identity):
    svc = InMemorySecurityService(default_ttl_seconds=3600)
    # Expired token with negative ttl
    token = svc.create_token(sample_identity, ttl=-10)

    with pytest.raises(TokenExpiredError):
        svc.verify_token(token)


def test_in_memory_password_hasher():
    hasher = InMemoryPasswordHasher()
    hashed = hasher.hash_password("secret")
    assert hashed == "mock_hash:secret"
    assert hasher.verify_password("secret", hashed) is True
    assert hasher.verify_password("wrong", hashed) is False
