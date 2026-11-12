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
from typing import Any

import pytest
from hypothesis import given
from hypothesis import strategies as st

from hexastack_core.adapters.circuit_breaker import (
    AsyncInMemoryCircuitBreaker,
    InMemoryCircuitBreaker,
)
from hexastack_core.adapters.storage import (
    AsyncInMemoryStorage,
    GcsStorageAdapter,
    InMemoryStorage,
    LocalStorageAdapter,
    OciStorageAdapter,
    S3StorageAdapter,
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


class _PropS3Client:
    def __init__(self) -> None:
        self.objects: dict[str, bytes] = {}

    def get_object(self, Bucket: str, Key: str) -> dict[str, Any]:
        import io

        if Key not in self.objects:
            msg = f"NoSuchKey: {Key}"
            raise Exception(msg)
        return {"Body": io.BytesIO(self.objects[Key])}

    def put_object(self, Bucket: str, Key: str, Body: bytes | Any) -> dict[str, Any]:
        self.objects[Key] = bytes(Body)
        return {}

    def delete_object(self, Bucket: str, Key: str) -> dict[str, Any]:
        self.objects.pop(Key, None)
        return {}

    def head_object(self, Bucket: str, Key: str) -> dict[str, Any]:
        if Key not in self.objects:
            msg = f"404 Not Found: {Key}"
            raise Exception(msg)
        return {}

    def list_objects_v2(
        self, Bucket: str, Prefix: str = "", **kwargs: Any
    ) -> dict[str, Any]:
        matches = [k for k in sorted(self.objects.keys()) if k.startswith(Prefix)]
        return {"Contents": [{"Key": k} for k in matches]}

    def generate_presigned_url(
        self, ClientMethod: str, Params: dict[str, Any], ExpiresIn: int = 3600
    ) -> str:
        return f"https://s3.amazonaws.com/{Params.get('Bucket')}/{Params.get('Key')}?action={ClientMethod}"


@given(
    path=clean_paths,
    content=data_bytes,
)
def test_storage_dual_oracle_s3_equivalence(path: str, content: bytes) -> None:
    """Dual-Oracle Property: S3StorageAdapter is functionally isomorphic to InMemoryStorage reference oracle."""
    oracle = InMemoryStorage()
    s3_adapter_inst = S3StorageAdapter(
        bucket_name="oracle-bucket", client=_PropS3Client()
    )

    # Initial state
    oracle_exists_before = oracle.exists(path)
    s3_exists_before = s3_adapter_inst.exists(path)
    assert s3_exists_before == oracle_exists_before
    assert s3_exists_before is False

    # Put operation
    oracle_put = oracle.put(path, content)
    s3_put = s3_adapter_inst.put(path, content)
    assert s3_put == oracle_put

    # Exists & Get
    oracle_exists = oracle.exists(path)
    s3_exists = s3_adapter_inst.exists(path)
    assert s3_exists == oracle_exists
    assert s3_exists is True

    oracle_val = oracle.get(path)
    s3_val = s3_adapter_inst.get(path)
    assert s3_val == oracle_val

    # List files
    oracle_files = oracle.list_files()
    s3_files = s3_adapter_inst.list_files()
    assert s3_files == oracle_files

    # Delete operation
    oracle_del = oracle.delete(path)
    s3_del = s3_adapter_inst.delete(path)
    assert s3_del == oracle_del

    # Post-delete state
    oracle_exists_after = oracle.exists(path)
    s3_exists_after = s3_adapter_inst.exists(path)
    assert s3_exists_after == oracle_exists_after
    assert s3_exists_after is False


class _PropGcsBlob:
    def __init__(self, name: str, bucket: _PropGcsBucket) -> None:
        self.name = name
        self.bucket = bucket

    def exists(self) -> bool:
        return self.name in self.bucket.blobs

    def download_as_bytes(self) -> bytes:
        return self.bucket.blobs[self.name]

    def upload_from_string(self, data: bytes) -> None:
        self.bucket.blobs[self.name] = bytes(data)

    def delete(self) -> None:
        self.bucket.blobs.pop(self.name, None)

    def generate_signed_url(self, **kwargs: Any) -> str:
        return f"https://storage.googleapis.com/{self.bucket.name}/{self.name}"


class _PropGcsBucket:
    def __init__(self, name: str) -> None:
        self.name = name
        self.blobs: dict[str, bytes] = {}

    def blob(self, path: str) -> _PropGcsBlob:
        return _PropGcsBlob(path, self)

    def list_blobs(self, prefix: str | None = None) -> list[_PropGcsBlob]:
        pfx = prefix or ""
        matches = [k for k in sorted(self.blobs.keys()) if k.startswith(pfx)]
        return [_PropGcsBlob(k, self) for k in matches]


class _PropGcsClient:
    def __init__(self) -> None:
        self.buckets: dict[str, _PropGcsBucket] = {}

    def bucket(self, name: str) -> _PropGcsBucket:
        if name not in self.buckets:
            self.buckets[name] = _PropGcsBucket(name)
        return self.buckets[name]


@given(
    path=clean_paths,
    content=data_bytes,
)
def test_storage_dual_oracle_gcs_equivalence(path: str, content: bytes) -> None:
    """Dual-Oracle Property: GcsStorageAdapter is functionally isomorphic to InMemoryStorage reference oracle."""
    oracle = InMemoryStorage()
    gcs_adapter_inst = GcsStorageAdapter(
        bucket_name="oracle-bucket", client=_PropGcsClient()
    )

    oracle_exists_before = oracle.exists(path)
    gcs_exists_before = gcs_adapter_inst.exists(path)
    assert gcs_exists_before == oracle_exists_before
    assert gcs_exists_before is False

    oracle_put = oracle.put(path, content)
    gcs_put = gcs_adapter_inst.put(path, content)
    assert gcs_put == oracle_put

    oracle_exists = oracle.exists(path)
    gcs_exists = gcs_adapter_inst.exists(path)
    assert gcs_exists == oracle_exists
    assert gcs_exists is True

    oracle_val = oracle.get(path)
    gcs_val = gcs_adapter_inst.get(path)
    assert gcs_val == oracle_val

    oracle_files = oracle.list_files()
    gcs_files = gcs_adapter_inst.list_files()
    assert gcs_files == oracle_files

    oracle_del = oracle.delete(path)
    gcs_del = gcs_adapter_inst.delete(path)
    assert gcs_del == oracle_del

    oracle_exists_after = oracle.exists(path)
    gcs_exists_after = gcs_adapter_inst.exists(path)
    assert gcs_exists_after == oracle_exists_after
    assert gcs_exists_after is False


class _PropOciResponse:
    def __init__(self, data: Any) -> None:
        self.data = data


class _PropOciServiceError(Exception):
    def __init__(self, message: str, status: int = 404) -> None:
        super().__init__(message)
        self.status = status


class _PropOciClient:
    def __init__(self) -> None:
        self.objects: dict[str, bytes] = {}

    def get_object(self, ns: str, b: str, obj: str) -> _PropOciResponse:
        if obj not in self.objects:
            raise _PropOciServiceError("NotFound", status=404)

        class _C:
            def __init__(self, c: bytes) -> None:
                self.content = c

        return _PropOciResponse(_C(self.objects[obj]))

    def put_object(self, ns: str, b: str, obj: str, body: Any) -> _PropOciResponse:
        self.objects[obj] = bytes(body)
        return _PropOciResponse({})

    def delete_object(self, ns: str, b: str, obj: str) -> _PropOciResponse:
        if obj not in self.objects:
            raise _PropOciServiceError("NotFound", status=404)
        del self.objects[obj]
        return _PropOciResponse({})

    def head_object(self, ns: str, b: str, obj: str) -> _PropOciResponse:
        if obj not in self.objects:
            raise _PropOciServiceError("NotFound", status=404)
        return _PropOciResponse({})

    def list_objects(
        self, ns: str, b: str, prefix: str | None = None
    ) -> _PropOciResponse:
        class _Obj:
            def __init__(self, name: str) -> None:
                self.name = name

        pfx = prefix or ""
        matches = [_Obj(k) for k in sorted(self.objects.keys()) if k.startswith(pfx)]
        return _PropOciResponse(matches)

    def create_preauthenticated_request(
        self, ns: str, b: str, details: Any
    ) -> _PropOciResponse:
        class _Par:
            access_uri = f"/p/token/{details.object_name}"
            full_path = None

        return _PropOciResponse(_Par())


@given(
    path=clean_paths,
    content=data_bytes,
)
def test_storage_dual_oracle_oci_equivalence(path: str, content: bytes) -> None:
    """Dual-Oracle Property: OciStorageAdapter is functionally isomorphic to InMemoryStorage reference oracle."""
    oracle = InMemoryStorage()
    oci_adapter_inst = OciStorageAdapter(
        bucket_name="b", namespace_name="ns", client=_PropOciClient()
    )

    oracle_exists_before = oracle.exists(path)
    oci_exists_before = oci_adapter_inst.exists(path)
    assert oci_exists_before == oracle_exists_before
    assert oci_exists_before is False

    oracle_put = oracle.put(path, content)
    oci_put = oci_adapter_inst.put(path, content)
    assert oci_put == oracle_put

    oracle_exists = oracle.exists(path)
    oci_exists = oci_adapter_inst.exists(path)
    assert oci_exists == oracle_exists
    assert oci_exists is True

    oracle_val = oracle.get(path)
    oci_val = oci_adapter_inst.get(path)
    assert oci_val == oracle_val

    oracle_files = oracle.list_files()
    oci_files = oci_adapter_inst.list_files()
    assert oci_files == oracle_files

    oracle_del = oracle.delete(path)
    oci_del = oci_adapter_inst.delete(path)
    assert oci_del == oracle_del

    oracle_exists_after = oracle.exists(path)
    oci_exists_after = oci_adapter_inst.exists(path)
    assert oci_exists_after == oracle_exists_after
    assert oci_exists_after is False
