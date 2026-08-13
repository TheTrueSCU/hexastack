from hexastack_auth.adapters.jwt import JwtSecurityAdapter
from hexastack_auth.adapters.password import Pbkdf2PasswordHasher
from hexastack_auth.domain.models import Identity
from hypothesis import given, settings
from hypothesis import strategies as st


@settings(max_examples=50)
@given(
    user_id=st.text(min_size=1, max_size=50),
    roles=st.lists(st.text(min_size=1, max_size=20), max_size=10, unique=True),
    permissions=st.lists(st.text(min_size=1, max_size=20), max_size=10, unique=True),
    tenant_id=st.one_of(st.none(), st.text(min_size=1, max_size=30)),
)
def test_jwt_identity_roundtrip_fuzzing(
    user_id: str,
    roles: list[str],
    permissions: list[str],
    tenant_id: str | None,
):
    adapter = JwtSecurityAdapter(
        secret_key="fuzz-secret-key-1234567890-secure",
        algorithm="HS256",
    )
    identity = Identity(
        user_id=user_id,
        roles=frozenset(roles),
        permissions=frozenset(permissions),
        tenant_id=tenant_id,
    )

    token = adapter.create_token(identity)
    decoded = adapter.verify_token(token)

    assert decoded.user_id == user_id
    assert decoded.roles == frozenset(roles)
    assert decoded.permissions == frozenset(permissions)
    assert decoded.tenant_id == tenant_id
    assert decoded.is_authenticated is True


@settings(max_examples=30)
@given(password=st.text(min_size=1, max_size=64))
def test_pbkdf2_password_hasher_fuzzing(password: str):
    hasher = Pbkdf2PasswordHasher(iterations=500)
    hashed = hasher.hash_password(password)

    assert hasher.verify_password(password, hashed) is True
    assert hasher.verify_password(password + "_wrong", hashed) is False
