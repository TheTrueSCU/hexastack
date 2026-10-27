"""Unit tests for InMemoryIdObfuscator.

Notes/Architectural Intent:
    Verifies that the reference in-memory Base62 obfuscator satisfies
    reversible round-trip identity, length, prefix, and error invariants.
"""

import pytest
from hypothesis import given
from hypothesis import strategies as st

from hexastack_core.adapters.identity.in_memory import InMemoryIdObfuscator


def test_in_memory_id_obfuscator_basic_roundtrip() -> None:
    """Test standard single integer encode and decode."""
    obfuscator = InMemoryIdObfuscator(min_length=6, prefix="test_")

    token = obfuscator.encode(42)
    assert token.startswith("test_")
    token_len = len(token)
    assert token_len >= 11  # "test_" (5) + min_length (6)

    decoded = obfuscator.decode(token)
    assert decoded == 42


def test_in_memory_id_obfuscator_zero() -> None:
    """Test encoding zero."""
    obfuscator = InMemoryIdObfuscator()
    token = obfuscator.encode(0)
    decoded = obfuscator.decode(token)
    assert decoded == 0


def test_in_memory_id_obfuscator_many() -> None:
    """Test encoding multiple integers in a composite token."""
    obfuscator = InMemoryIdObfuscator(prefix="item_")
    numbers = (1, 100, 9999)

    token = obfuscator.encode_many(numbers)
    assert "-" in token

    decoded = obfuscator.decode_many(token)
    assert decoded == numbers


def test_in_memory_id_obfuscator_negative_raises() -> None:
    """Test that negative numbers raise ValueError."""
    obfuscator = InMemoryIdObfuscator()

    with pytest.raises(ValueError, match="negative"):
        obfuscator.encode(-1)

    with pytest.raises(ValueError, match="negative"):
        obfuscator.encode_many([1, -5, 3])


def test_in_memory_id_obfuscator_empty_raises() -> None:
    """Test that empty sequences raise ValueError."""
    obfuscator = InMemoryIdObfuscator()

    with pytest.raises(ValueError, match="empty"):
        obfuscator.encode_many([])

    with pytest.raises(ValueError, match="Invalid token"):
        obfuscator.decode("")

    with pytest.raises(ValueError, match="Invalid composite"):
        obfuscator.decode_many("")


def test_in_memory_id_obfuscator_invalid_prefix_raises() -> None:
    """Test that mismatching prefix raises ValueError."""
    obfuscator = InMemoryIdObfuscator(prefix="sec_")

    with pytest.raises(ValueError, match="missing expected prefix"):
        obfuscator.decode("wrong_123")


def test_in_memory_id_obfuscator_invalid_min_length_raises() -> None:
    """Test that negative min_length raises ValueError."""
    with pytest.raises(ValueError, match="non-negative"):
        InMemoryIdObfuscator(min_length=-1)


@given(st.integers(min_value=0, max_value=10_000_000))
def test_in_memory_id_obfuscator_hypothesis_roundtrip(val: int) -> None:
    """Property test proving round-trip reversibility across the non-negative integer domain."""
    obfuscator = InMemoryIdObfuscator(min_length=4)
    token = obfuscator.encode(val)
    decoded = obfuscator.decode(token)
    assert decoded == val
