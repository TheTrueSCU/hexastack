"""Unit and dual-oracle verification tests for HashidsAdapter.

Notes/Architectural Intent:
    Verifies that HashidsAdapter satisfies IdObfuscatorPort contracts,
    handles custom salts/alphabets, and maintains mathematical round-trip
    invariants cross-evaluated against the reference InMemoryIdObfuscator.
"""

import pytest
from hypothesis import given
from hypothesis import strategies as st

from hexastack_core.adapters.identity.hashids import HashidsAdapter
from hexastack_core.adapters.identity.in_memory import InMemoryIdObfuscator
from hexastack_core.exceptions import MissingDependencyError


def test_hashids_adapter_basic_roundtrip() -> None:
    """Test standard single integer encode and decode with salt and min_length."""
    adapter = HashidsAdapter(salt="tenant_alpha", min_length=10)

    token = adapter.encode(12345)
    token_len = len(token)
    assert token_len >= 10

    decoded = adapter.decode(token)
    assert decoded == 12345


def test_hashids_adapter_zero() -> None:
    """Test encoding zero with Hashids."""
    adapter = HashidsAdapter(salt="zero_test")
    token = adapter.encode(0)
    decoded = adapter.decode(token)
    assert decoded == 0


def test_hashids_adapter_many() -> None:
    """Test encoding multiple integers in a composite token."""
    adapter = HashidsAdapter(salt="multi_tenant", min_length=8)
    numbers = (42, 999, 100000)

    token = adapter.encode_many(numbers)
    token_len = len(token)
    assert token_len >= 8

    decoded = adapter.decode_many(token)
    assert decoded == numbers


def test_hashids_adapter_salt_separation() -> None:
    """Test that distinct salts generate distinct tokens for the same integer."""
    adapter1 = HashidsAdapter(salt="tenant_1")
    adapter2 = HashidsAdapter(salt="tenant_2")

    token1 = adapter1.encode(500)
    token2 = adapter2.encode(500)

    assert token1 != token2
    decoded1 = adapter1.decode(token1)
    assert decoded1 == 500

    # Cross-decoding with the wrong salt must fail to prevent cross-tenant correlation
    with pytest.raises(ValueError, match="Invalid or undecodable token"):
        adapter2.decode(token1)


def test_hashids_adapter_custom_alphabet() -> None:
    """Test Hashids with custom uppercase-only alphabet."""
    alphabet = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"  # pragma: allowlist secret
    adapter = HashidsAdapter(alphabet=alphabet, min_length=6)

    token = adapter.encode(777)
    decoded = adapter.decode(token)
    assert decoded == 777

    for char in token:
        assert char in alphabet


def test_hashids_adapter_negative_raises() -> None:
    """Test that negative numbers raise ValueError."""
    adapter = HashidsAdapter()

    with pytest.raises(ValueError, match="negative"):
        adapter.encode(-1)

    with pytest.raises(ValueError, match="negative"):
        adapter.encode_many([10, -3])


def test_hashids_adapter_empty_raises() -> None:
    """Test that empty inputs raise ValueError."""
    adapter = HashidsAdapter()

    with pytest.raises(ValueError, match="empty"):
        adapter.encode_many([])

    with pytest.raises(ValueError, match="Invalid token"):
        adapter.decode("")

    with pytest.raises(ValueError, match="Invalid composite"):
        adapter.decode_many("")


def test_hashids_adapter_invalid_min_length_raises() -> None:
    """Test that negative min_length raises ValueError."""
    with pytest.raises(ValueError, match="non-negative"):
        HashidsAdapter(min_length=-5)


def test_hashids_adapter_missing_package(monkeypatch: pytest.MonkeyPatch) -> None:
    """Test that missing hashids library raises helpful MissingDependencyError."""
    import sys

    monkeypatch.setitem(sys.modules, "hashids", None)

    with pytest.raises(MissingDependencyError, match="hexastack-core\\[identity\\]"):
        HashidsAdapter()


@given(
    val=st.integers(min_value=0, max_value=50_000_000),
    salt=st.text(min_size=0, max_size=20),
    min_length=st.integers(min_value=0, max_value=16),
)
def test_hashids_dual_oracle_roundtrip(val: int, salt: str, min_length: int) -> None:
    """Dual-oracle testing: verify round-trip contract parity against InMemoryIdObfuscator."""
    hashids_adapter = HashidsAdapter(salt=salt, min_length=min_length)
    oracle_adapter = InMemoryIdObfuscator(min_length=min_length)

    token_prod = hashids_adapter.encode(val)
    token_oracle = oracle_adapter.encode(val)

    # Invariant 1: Both tokens respect the minimum length constraint
    len_prod = len(token_prod)
    len_oracle = len(token_oracle)
    assert len_prod >= min_length
    assert len_oracle >= min_length

    # Invariant 2: Both decoders accurately recover the identical integer
    decoded_prod = hashids_adapter.decode(token_prod)
    decoded_oracle = oracle_adapter.decode(token_oracle)

    assert decoded_prod == val
    assert decoded_oracle == val
    assert decoded_prod == decoded_oracle
