"""Hypothesis property-based tests for JWT encoding, decoding, and tampering invariants.

Notes/Architectural Intent:
    Verifies that for arbitrary user identities (alphanumeric, unicode, complex roles,
    custom claims, and varied tenant configurations), JWT encode/decode roundtrips
    are mathematically isomorphic, non-empty tokens with altered payload bits fail
    signature verification, and expired tokens deterministically raise TokenExpiredError.
"""

from datetime import timedelta

import pytest
from hypothesis import given
from hypothesis import strategies as st

from hexastack_auth.adapters.jwt import JwtSecurityAdapter
from hexastack_auth.domain.exceptions import (
    InvalidTokenError,
    TokenExpiredError,
)
from hexastack_auth.domain.models import Identity

# Strategy for generating realistic and edge-case Identity objects
valid_strings = st.text(
    alphabet=st.characters(blacklist_categories=("Cs", "Cc")),
    min_size=1,
    max_size=64,
)
valid_roles = st.frozensets(
    st.text(
        alphabet=st.characters(whitelist_categories=("Ll", "Nd")),
        min_size=1,
        max_size=32,
    ),
    max_size=10,
)
valid_claims = st.dictionaries(
    keys=st.text(
        alphabet=st.characters(whitelist_categories=("Ll",)),
        min_size=1,
        max_size=16,
    ).filter(
        lambda k: (
            k
            not in {
                "sub",
                "roles",
                "permissions",
                "iat",
                "exp",
                "tenant_id",
                "iss",
                "aud",
            }
        )
    ),
    values=st.one_of(
        st.booleans(),
        st.integers(min_value=-1000000, max_value=1000000),
        st.text(min_size=0, max_size=64),
    ),
    max_size=5,
)

identities = st.builds(
    Identity,
    user_id=valid_strings,
    roles=valid_roles,
    permissions=valid_roles,
    tenant_id=st.one_of(st.none(), valid_strings),
    claims=valid_claims,
    is_authenticated=st.just(True),
)

secret_keys = st.text(
    alphabet=st.characters(blacklist_categories=("Cs", "Cc")),
    min_size=32,
    max_size=64,
)


@given(secret=secret_keys, identity=identities)
def test_jwt_encode_decode_roundtrip_isomorphism(secret: str, identity: Identity):
    """Property: Any valid Identity encoded to JWT and decoded returns equivalent Identity."""
    adapter = JwtSecurityAdapter(secret_key=secret, default_ttl_seconds=3600)
    token = adapter.create_token(identity)

    assert isinstance(token, str)
    assert len(token) > 0

    decoded = adapter.verify_token(token)
    assert decoded.user_id == identity.user_id
    assert decoded.roles == identity.roles
    assert decoded.permissions == identity.permissions
    assert decoded.tenant_id == identity.tenant_id
    assert decoded.is_authenticated is True

    # Custom claims preserved
    for k, v in identity.claims.items():
        assert decoded.claims.get(k) == v


@given(secret=secret_keys, identity=identities)
def test_jwt_tampering_fails_verification(secret: str, identity: Identity):
    """Property: Modifying any bit in the signed JWT payload or signature fails validation."""
    adapter = JwtSecurityAdapter(secret_key=secret)
    token = adapter.create_token(identity)

    parts = token.split(".")
    if len(parts) == 3:
        header, payload, signature = parts
        # Tamper payload by altering a character
        tampered_payload = (
            payload[:-1] + ("A" if payload[-1] != "A" else "B")
            if payload
            else "eyJhbGciOiJIUzI1NiJ9"
        )
        tampered_token = f"{header}.{tampered_payload}.{signature}"

        with pytest.raises(InvalidTokenError):
            adapter.verify_token(tampered_token)


@given(secret=secret_keys, identity=identities)
def test_jwt_expired_token_raises_token_expired_error(secret: str, identity: Identity):
    """Property: Negative TTL guarantees immediate TokenExpiredError."""
    adapter = JwtSecurityAdapter(secret_key=secret)
    expired_token = adapter.create_token(identity, ttl=timedelta(seconds=-10))

    with pytest.raises(TokenExpiredError):
        adapter.verify_token(expired_token)
