"""Unit tests for GcsStorageAdapter and AsyncGcsStorageAdapter."""

from __future__ import annotations

import io
from typing import Any

import pytest

from hexastack_core.adapters.storage import gcs as gcs_adapter
from hexastack_core.domain.exceptions import (
    MissingDependencyError,
    StorageError,
    StorageNotFoundError,
)


class MockBlob:
    """Mock Google Cloud Storage Blob."""

    def __init__(self, name: str, bucket: MockBucket) -> None:
        self.name = name
        self.bucket = bucket

    def exists(self) -> bool:
        return self.name in self.bucket.blobs

    def download_as_bytes(self) -> bytes:
        if not self.exists():
            msg = f"Blob {self.name} not found"
            raise FileNotFoundError(msg)
        return self.bucket.blobs[self.name]

    def upload_from_string(self, data: bytes) -> None:
        self.bucket.blobs[self.name] = bytes(data)

    def upload_from_file(self, file_obj: Any) -> None:
        self.bucket.blobs[self.name] = file_obj.read()

    def delete(self) -> None:
        if not self.exists():
            msg = f"Blob {self.name} not found"
            raise FileNotFoundError(msg)
        del self.bucket.blobs[self.name]

    def generate_signed_url(self, **kwargs: Any) -> str:
        method = kwargs.get("method", "GET")
        expiration = kwargs.get("expiration")
        ct = kwargs.get("content_type", "")
        ct_param = f"&content_type={ct}" if ct else ""
        return (
            f"https://storage.googleapis.com/{self.bucket.name}/{self.name}"
            f"?method={method}&expiration={expiration}{ct_param}"
        )


class MockBucket:
    """Mock Google Cloud Storage Bucket."""

    def __init__(self, name: str) -> None:
        self.name = name
        self.blobs: dict[str, bytes] = {}

    def blob(self, path: str) -> MockBlob:
        return MockBlob(path, self)

    def list_blobs(self, prefix: str | None = None) -> list[MockBlob]:
        prefix_str = prefix or ""
        matches = [k for k in sorted(self.blobs.keys()) if k.startswith(prefix_str)]
        return [MockBlob(k, self) for k in matches]


class MockGcsClient:
    """Mock Google Cloud Storage Client."""

    def __init__(self) -> None:
        self.buckets: dict[str, MockBucket] = {}

    def bucket(self, name: str) -> MockBucket:
        if name not in self.buckets:
            self.buckets[name] = MockBucket(name)
        return self.buckets[name]


def test_gcs_storage_adapter_crud_and_presigned() -> None:
    """Verify synchronous GcsStorageAdapter operations with mock client."""
    client = MockGcsClient()
    storage = gcs_adapter.GcsStorageAdapter(bucket_name="my-gcs-bucket", client=client)

    # Exists & Get non-existent
    exists_before = storage.exists("blob.dat")
    assert exists_before is False
    with pytest.raises(StorageNotFoundError, match="GCS blob not found"):
        storage.get("blob.dat")

    # Put bytes
    res_put = storage.put("blob.dat", b"GCS byte content")
    assert res_put == "blob.dat"
    exists_after = storage.exists("blob.dat")
    assert exists_after is True
    val = storage.get("blob.dat")
    assert val == b"GCS byte content"

    # Put stream
    stream = io.BytesIO(b"GCS stream content")
    res_stream = storage.put("sub/stream.dat", stream)
    assert res_stream == "sub/stream.dat"
    val_stream = storage.get("sub/stream.dat")
    assert val_stream == b"GCS stream content"

    # Presigned URLs
    upload_url = storage.generate_presigned_upload_url(
        "sub/upload.tar.gz",
        expires_in_seconds=1800,
        content_type="application/gzip",
    )
    assert (
        "https://storage.googleapis.com/my-gcs-bucket/sub/upload.tar.gz" in upload_url
    )
    assert "method=PUT" in upload_url
    assert "content_type=application/gzip" in upload_url

    download_url = storage.generate_presigned_download_url(
        "blob.dat",
        expires_in_seconds=3600,
    )
    assert "https://storage.googleapis.com/my-gcs-bucket/blob.dat" in download_url
    assert "method=GET" in download_url

    # List files
    files = storage.list_files("sub/")
    assert files == ["sub/stream.dat"]

    # Delete
    del_res = storage.delete("blob.dat")
    assert del_res is True
    exists_del = storage.exists("blob.dat")
    assert exists_del is False
    del_nonexistent = storage.delete("blob.dat")
    assert del_nonexistent is False


def test_gcs_storage_adapter_error_handling() -> None:
    """Verify GcsStorageAdapter error wrapping."""

    class BrokenBucket:
        def blob(self, path: str) -> Any:
            msg = "Bucket access denied"
            raise PermissionError(msg)

        def list_blobs(self, **kwargs: Any) -> Any:
            msg = "List error"
            raise RuntimeError(msg)

    class BrokenGcsClient:
        def bucket(self, name: str) -> Any:
            return BrokenBucket()

    storage = gcs_adapter.GcsStorageAdapter(
        bucket_name="broken-bucket", client=BrokenGcsClient()
    )

    with pytest.raises(StorageError, match="Failed to retrieve GCS blob"):
        storage.get("error.dat")

    with pytest.raises(StorageError, match="Failed to persist GCS blob"):
        storage.put("error.dat", b"payload")

    with pytest.raises(StorageError, match="Failed to delete GCS blob"):
        storage.delete("error.dat")

    with pytest.raises(StorageError, match="Failed to check GCS blob existence"):
        storage.exists("error.dat")

    with pytest.raises(StorageError, match="Failed to list GCS blobs"):
        storage.list_files()

    with pytest.raises(
        StorageError, match="Failed to generate GCS presigned upload URL"
    ):
        storage.generate_presigned_upload_url("error.dat")

    with pytest.raises(
        StorageError, match="Failed to generate GCS presigned download URL"
    ):
        storage.generate_presigned_download_url("error.dat")

    # Invalid data type
    invalid_data: Any = 1234
    storage_mock = gcs_adapter.GcsStorageAdapter(
        bucket_name="b", client=MockGcsClient()
    )
    with pytest.raises(StorageError, match="Unsupported data type"):
        storage_mock.put("err.dat", invalid_data)


def test_gcs_init_kwargs(monkeypatch: pytest.MonkeyPatch) -> None:
    """Verify GcsStorageAdapter client initialization with project and credentials."""
    captured: dict[str, Any] = {}

    class FakeStorageMod:
        class Client:
            def __init__(
                self, project: str | None = None, credentials: Any = None
            ) -> None:
                captured["project"] = project
                captured["credentials"] = credentials

    monkeypatch.setattr(
        gcs_adapter, "require_dependency", lambda *args, **kwargs: FakeStorageMod
    )
    gcs_adapter.GcsStorageAdapter(
        bucket_name="my-bucket", project="my-project", credentials="my-credentials"
    )
    assert captured["project"] == "my-project"
    assert captured["credentials"] == "my-credentials"


def test_gcs_missing_dependency(monkeypatch: pytest.MonkeyPatch) -> None:
    """Verify MissingDependencyError when google-cloud-storage is not installed."""
    import sys

    monkeypatch.setitem(sys.modules, "google.cloud.storage", None)
    with pytest.raises(MissingDependencyError, match="google.cloud.storage"):
        gcs_adapter.GcsStorageAdapter(bucket_name="my-bucket")


@pytest.mark.anyio
async def test_async_gcs_storage_adapter() -> None:
    """Verify asynchronous AsyncGcsStorageAdapter operations."""
    client = MockGcsClient()
    storage = gcs_adapter.AsyncGcsStorageAdapter(
        bucket_name="async-bucket", client=client
    )

    exists_init = await storage.exists_async("async.dat")
    assert exists_init is False

    res_put = await storage.put_async("async.dat", b"Async GCS bytes")
    assert res_put == "async.dat"

    exists_put = await storage.exists_async("async.dat")
    assert exists_put is True

    val = await storage.get_async("async.dat")
    assert val == b"Async GCS bytes"

    up_url = await storage.generate_presigned_upload_url_async(
        "async.dat", expires_in_seconds=600
    )
    assert "https://storage.googleapis.com/async-bucket/async.dat" in up_url

    up_alias = await storage.generate_presigned_upload_url(
        "async.dat", expires_in_seconds=600
    )
    assert "https://storage.googleapis.com/async-bucket/async.dat" in up_alias

    down_url = await storage.generate_presigned_download_url_async(
        "async.dat", expires_in_seconds=600
    )
    assert "https://storage.googleapis.com/async-bucket/async.dat" in down_url

    down_alias = await storage.generate_presigned_download_url(
        "async.dat", expires_in_seconds=600
    )
    assert "https://storage.googleapis.com/async-bucket/async.dat" in down_alias

    files = await storage.list_files_async()
    assert files == ["async.dat"]

    res_del = await storage.delete_async("async.dat")
    assert res_del is True
    exists_del = await storage.exists_async("async.dat")
    assert exists_del is False
