import pytest
from hexastack_auth.adapters.in_memory import (
    InMemoryPasswordHasher,
    InMemorySecurityService,
)
from hexastack_auth.adapters.jwt import JwtSecurityAdapter
from hexastack_auth.adapters.password import Pbkdf2PasswordHasher
from hexastack_auth.domain.models import Identity
from hexastack_core.utils.context import set_user_context


@pytest.fixture
def mock_security() -> InMemorySecurityService:
    """Fixture providing a clean in-memory security token service."""
    return InMemorySecurityService()


@pytest.fixture
def mock_hasher() -> InMemoryPasswordHasher:
    """Fixture providing a clean in-memory password hasher."""
    return InMemoryPasswordHasher()


@pytest.fixture
def jwt_security() -> JwtSecurityAdapter:
    """Fixture providing a standard JWT security adapter."""
    return JwtSecurityAdapter(
        secret_key="test-secret-key-1234567890-test-key",
        algorithm="HS256",
        default_ttl_seconds=3600,
        issuer="hexastack-test",
        audience="hexastack-aud",
    )


@pytest.fixture
def pbkdf2_hasher() -> Pbkdf2PasswordHasher:
    """Fixture providing a fast-iteration PBKDF2 hasher for tests."""
    return Pbkdf2PasswordHasher(iterations=1000)


@pytest.fixture
def sample_identity() -> Identity:
    """Fixture providing a sample authenticated Identity."""
    return Identity(
        user_id="usr_123",
        roles=frozenset(["admin", "editor"]),
        permissions=frozenset(["articles:read", "articles:write", "users:ban"]),
        tenant_id="tenant_abc",
        claims={"email": "admin@hexastack.io"},
    )


@pytest.fixture(autouse=True)
def clean_user_context():
    """Autouse fixture resetting user context between tests."""
    set_user_context(None)
    yield
    set_user_context(None)
