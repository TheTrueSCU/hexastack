"""Hypothesis property-based tests for CircuitBreakerPort and StoragePort invariants.

Notes/Architectural Intent:
    Fuzzes arbitrary sequences of operations to prove state machine and I/O correctness:
    1. CircuitBreaker State Machine Invariants:
       - Failure threshold transition: exactly `failure_threshold` failures in CLOSED state trips to OPEN.
       - OPEN state rejection: `allow_execution()` is always False while in OPEN before recovery timeout.
       - Reset invariant: `reset()` unconditionally returns state to CLOSED and clears failure counts.
       - Success idempotency: in CLOSED state, successes never alter CLOSED state and keep failure_count at 0.
    2. Storage Adapter Round-Trip Invariants (InMemoryStorage & LocalStorageAdapter):
       - Put-Get isomorphism: `get(path) == data` for any arbitrary byte sequences and paths.
       - Exists consistency: `exists(path)` is True iff file was put and not deleted.
       - Delete idempotency: `delete(path)` returns True on first delete, False on subsequent.
"""

from __future__ import annotations

import string
import tempfile

import pytest
from hypothesis import given
from hypothesis import strategies as st

from hexastack_core.adapters.circuit_breaker import (
    AsyncInMemoryCircuitBreaker,
    InMemoryCircuitBreaker,
)
from hexastack_core.adapters.storage import (
    AsyncInMemoryStorage,
    InMemoryStorage,
    LocalStorageAdapter,
)
from hexastack_core.ports.circuit_breaker import CircuitState

# Strategies
valid_names = st.text(
    alphabet=string.ascii_letters + string.digits + "_",
    min_size=1,
    max_size=32,
)
clean_paths = st.text(
    alphabet=string.ascii_lowercase + string.digits + "_-",
    min_size=1,
    max_size=20,
).map(lambda s: f"files/{s}.dat")
data_bytes = st.binary(min_size=0, max_size=4096)


@given(
    breaker_name=valid_names,
    threshold=st.integers(min_value=1, max_value=20),
    failures_before_trip=st.integers(min_value=0, max_value=50),
)
def test_circuit_breaker_failure_threshold_invariants(
    breaker_name: str, threshold: int, failures_before_trip: int
) -> None:
    """Property: Circuit breaker remains CLOSED until failure count reaches threshold, then transitions to OPEN."""
    breaker = InMemoryCircuitBreaker(
        failure_threshold=threshold, recovery_timeout_seconds=3600.0
    )

    assert breaker.state(breaker_name) == CircuitState.CLOSED
    assert breaker.allow_execution(breaker_name) is True

    for i in range(failures_before_trip):
        breaker.record_failure(breaker_name, RuntimeError("test error"))
        if i + 1 < threshold:
            assert breaker.state(breaker_name) == CircuitState.CLOSED
            assert breaker.allow_execution(breaker_name) is True
        else:
            assert breaker.state(breaker_name) == CircuitState.OPEN
            assert breaker.allow_execution(breaker_name) is False

    # Reset invariant
    breaker.reset(breaker_name)
    assert breaker.state(breaker_name) == CircuitState.CLOSED
    assert breaker.allow_execution(breaker_name) is True


@given(
    breaker_name=valid_names,
    threshold=st.integers(min_value=1, max_value=10),
    success_count=st.integers(min_value=1, max_value=20),
)
def test_circuit_breaker_success_invariants(
    breaker_name: str, threshold: int, success_count: int
) -> None:
    """Property: Successes in CLOSED state keep breaker CLOSED and reset accumulated partial failures."""
    breaker = InMemoryCircuitBreaker(
        failure_threshold=threshold, recovery_timeout_seconds=3600.0
    )

    # Accumulate threshold - 1 failures
    for _ in range(threshold - 1):
        breaker.record_failure(breaker_name)

    assert breaker.state(breaker_name) == CircuitState.CLOSED

    # Record success
    for _ in range(success_count):
        breaker.record_success(breaker_name)
        assert breaker.state(breaker_name) == CircuitState.CLOSED

    # An additional single failure should NOT trip it, since failure count was reset
    if threshold > 1:
        breaker.record_failure(breaker_name)
        assert breaker.state(breaker_name) == CircuitState.CLOSED


@pytest.mark.anyio
@given(
    breaker_name=valid_names,
    threshold=st.integers(min_value=1, max_value=15),
    failures=st.integers(min_value=1, max_value=30),
)
async def test_async_circuit_breaker_properties(
    breaker_name: str, threshold: int, failures: int
) -> None:
    """Property: AsyncInMemoryCircuitBreaker conforms to identical threshold and trip invariants."""
    breaker = AsyncInMemoryCircuitBreaker(
        failure_threshold=threshold, recovery_timeout_seconds=3600.0
    )

    for i in range(failures):
        await breaker.record_failure_async(breaker_name)
        if i + 1 < threshold:
            assert await breaker.state_async(breaker_name) == CircuitState.CLOSED
        else:
            assert await breaker.state_async(breaker_name) == CircuitState.OPEN
            assert await breaker.allow_execution_async(breaker_name) is False

    await breaker.reset_async(breaker_name)
    assert await breaker.state_async(breaker_name) == CircuitState.CLOSED


@given(
    path=clean_paths,
    content=data_bytes,
)
def test_in_memory_storage_roundtrip_properties(path: str, content: bytes) -> None:
    """Property: InMemoryStorage preserves data exactly and maintains strict lifecycle invariants."""
    storage = InMemoryStorage()

    assert storage.exists(path) is False
    res_path = storage.put(path, content)
    assert res_path == path
    assert storage.exists(path) is True
    assert storage.get(path) == content

    # File listing consistency
    files = storage.list_files()
    assert path in files

    # Deletion consistency
    first_del = storage.delete(path)
    assert first_del is True
    assert storage.exists(path) is False
    second_del = storage.delete(path)
    assert second_del is False


@given(
    path=clean_paths,
    content=data_bytes,
)
def test_local_storage_roundtrip_properties(path: str, content: bytes) -> None:
    """Property: LocalStorageAdapter preserves data exactly and handles nested paths reliably."""
    with tempfile.TemporaryDirectory() as tmpdir:
        storage = LocalStorageAdapter(root_dir=tmpdir)

        assert storage.exists(path) is False
        res_path = storage.put(path, content)
        assert res_path == path
        assert storage.exists(path) is True
        assert storage.get(path) == content

        # Deletion consistency
        first_del = storage.delete(path)
        assert first_del is True
        assert storage.exists(path) is False
        second_del = storage.delete(path)
        assert second_del is False


@pytest.mark.anyio
@given(
    path=clean_paths,
    content=data_bytes,
)
async def test_async_in_memory_storage_properties(path: str, content: bytes) -> None:
    """Property: AsyncInMemoryStorage maintains full async parity and data integrity."""
    storage = AsyncInMemoryStorage()

    assert await storage.exists_async(path) is False
    res_path = await storage.put_async(path, content)
    assert res_path == path
    assert await storage.exists_async(path) is True
    assert await storage.get_async(path) == content

    first_del = await storage.delete_async(path)
    assert first_del is True
    assert await storage.exists_async(path) is False
