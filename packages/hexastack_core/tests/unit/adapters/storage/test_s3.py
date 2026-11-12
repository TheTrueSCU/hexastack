"""Unit tests for S3StorageAdapter and AsyncS3StorageAdapter."""

from __future__ import annotations

import io
from typing import Any, cast

import pytest

from hexastack_core.adapters.storage import s3 as s3_adapter
from hexastack_core.domain.exceptions import (
    MissingDependencyError,
    StorageError,
    StorageNotFoundError,
)


class MockS3Client:
    """Mock boto3 S3 client for hermetic testing."""

    def __init__(self) -> None:
        self.objects: dict[str, bytes] = {}

    def get_object(self, Bucket: str, Key: str) -> dict[str, Any]:
        if Key not in self.objects:
            msg = f"NoSuchKey: {Key} not found in {Bucket}"
            raise Exception(msg)
        return {"Body": io.BytesIO(self.objects[Key])}

    def put_object(self, Bucket: str, Key: str, Body: bytes | Any) -> dict[str, Any]:
        if isinstance(Body, (bytes, bytearray)):
            self.objects[Key] = bytes(Body)
        elif hasattr(Body, "read"):
            self.objects[Key] = Body.read()
        else:
            self.objects[Key] = bytes(Body)
        return {"ETag": "mock-etag"}

    def delete_object(self, Bucket: str, Key: str) -> dict[str, Any]:
        self.objects.pop(Key, None)
        return {}

    def head_object(self, Bucket: str, Key: str) -> dict[str, Any]:
        if Key not in self.objects:
            msg = f"404 Not Found: {Key}"
            raise Exception(msg)
        return {"ContentLength": len(self.objects[Key])}

    def list_objects_v2(
        self,
        Bucket: str,
        Prefix: str = "",
        ContinuationToken: str | None = None,
    ) -> dict[str, Any]:
        matches = [k for k in sorted(self.objects.keys()) if k.startswith(Prefix)]
        return {"Contents": [{"Key": k} for k in matches]}

    def generate_presigned_url(
        self,
        ClientMethod: str,
        Params: dict[str, Any],
        ExpiresIn: int = 3600,
    ) -> str:
        bucket = Params.get("Bucket", "")
        key = Params.get("Key", "")
        ct = Params.get("ContentType", "")
        ct_param = f"&content_type={ct}" if ct else ""
        return f"https://s3.amazonaws.com/{bucket}/{key}?method={ClientMethod}&expires={ExpiresIn}{ct_param}"


def test_s3_storage_adapter_crud_and_presigned() -> None:
    """Verify synchronous S3StorageAdapter operations with mock client."""
    client = MockS3Client()
    storage = s3_adapter.S3StorageAdapter(bucket_name="my-bucket", client=client)

    # Exists & Get non-existent
    exists_before = storage.exists("obj1.dat")
    assert exists_before is False
    with pytest.raises(StorageNotFoundError, match="S3 object not found"):
        storage.get("obj1.dat")

    # Put bytes
    res_put = storage.put("obj1.dat", b"S3 byte payload")
    assert res_put == "obj1.dat"
    exists_after = storage.exists("obj1.dat")
    assert exists_after is True
    val = storage.get("obj1.dat")
    assert val == b"S3 byte payload"

    # Put stream
    stream = io.BytesIO(b"S3 stream payload")
    res_stream = storage.put("sub/stream.dat", stream)
    assert res_stream == "sub/stream.dat"
    val_stream = storage.get("sub/stream.dat")
    assert val_stream == b"S3 stream payload"

    # Put stream with str
    class S3StringReader:
        def read(self) -> str:
            return "S3 string content"

    res_str = storage.put("sub/str.txt", cast("Any", S3StringReader()))
    assert res_str == "sub/str.txt"
    val_str = storage.get("sub/str.txt")
    assert val_str == b"S3 string content"

    # Presigned URLs
    upload_url = storage.generate_presigned_upload_url(
        "sub/upload.tar.gz",
        expires_in_seconds=1800,
        content_type="application/gzip",
    )
    assert "https://s3.amazonaws.com/my-bucket/sub/upload.tar.gz" in upload_url
    assert "method=put_object" in upload_url
    assert "content_type=application/gzip" in upload_url

    download_url = storage.generate_presigned_download_url(
        "obj1.dat",
        expires_in_seconds=7200,
    )
    assert "https://s3.amazonaws.com/my-bucket/obj1.dat" in download_url
    assert "method=get_object" in download_url
    assert "expires=7200" in download_url

    # List files
    files = storage.list_files("sub/")
    assert files == ["sub/str.txt", "sub/stream.dat"]

    # Pagination test in list_files
    class PaginatedMockS3Client(MockS3Client):
        def list_objects_v2(
            self, Bucket: str, Prefix: str = "", ContinuationToken: str | None = None
        ) -> dict[str, Any]:
            if ContinuationToken is None:
                return {
                    "Contents": [{"Key": "p1.dat"}],
                    "NextContinuationToken": "token-2",
                }
            return {"Contents": [{"Key": "p2.dat"}]}

    paginated_storage = s3_adapter.S3StorageAdapter(
        bucket_name="my-bucket", client=PaginatedMockS3Client()
    )
    paginated_files = paginated_storage.list_files()
    assert paginated_files == ["p1.dat", "p2.dat"]

    # Delete
    res_del = storage.delete("obj1.dat")
    assert res_del is True
    exists_deleted = storage.exists("obj1.dat")
    assert exists_deleted is False


def test_s3_storage_adapter_error_handling() -> None:
    """Verify S3StorageAdapter error wrapping."""

    class BrokenS3Client:
        def get_object(self, Bucket: str, Key: str) -> dict[str, Any]:
            msg = "Fatal S3 network partition"
            raise ConnectionError(msg)

        def put_object(self, Bucket: str, Key: str, Body: Any) -> dict[str, Any]:
            msg = "S3 bucket full"
            raise OSError(msg)

        def delete_object(self, Bucket: str, Key: str) -> dict[str, Any]:
            msg = "Access Denied 403"
            raise PermissionError(msg)

        def head_object(self, Bucket: str, Key: str) -> dict[str, Any]:
            msg = "Internal Error 500"
            raise RuntimeError(msg)

        def list_objects_v2(self, **kwargs: Any) -> dict[str, Any]:
            msg = "List error"
            raise RuntimeError(msg)

        def generate_presigned_url(self, **kwargs: Any) -> str:
            msg = "Presign error"
            raise RuntimeError(msg)

    storage = s3_adapter.S3StorageAdapter(
        bucket_name="broken-bucket", client=BrokenS3Client()
    )

    with pytest.raises(StorageError, match="Failed to retrieve S3 object"):
        storage.get("error.dat")

    with pytest.raises(StorageError, match="Failed to persist S3 object"):
        storage.put("error.dat", b"payload")

    with pytest.raises(StorageError, match="Failed to delete S3 object"):
        storage.delete("error.dat")

    with pytest.raises(StorageError, match="Failed to check S3 object existence"):
        storage.exists("error.dat")

    with pytest.raises(StorageError, match="Failed to list S3 objects"):
        storage.list_files()

    with pytest.raises(
        StorageError, match="Failed to generate S3 presigned upload URL"
    ):
        storage.generate_presigned_upload_url("error.dat")

    with pytest.raises(
        StorageError, match="Failed to generate S3 presigned download URL"
    ):
        storage.generate_presigned_download_url("error.dat")

    # Invalid data type
    invalid_data: Any = 9999
    with pytest.raises(StorageError, match="Unsupported data type"):
        storage.put("invalid.dat", invalid_data)


def test_s3_init_kwargs(monkeypatch: pytest.MonkeyPatch) -> None:
    """Verify S3StorageAdapter client initialization with credentials and custom endpoint."""
    captured_kwargs: dict[str, Any] = {}

    class FakeBoto3:
        @staticmethod
        def client(service_name: str, **kwargs: Any) -> MockS3Client:
            captured_kwargs.update(kwargs)
            return MockS3Client()

    monkeypatch.setattr(
        s3_adapter, "require_dependency", lambda *args, **kwargs: FakeBoto3
    )
    s3_adapter.S3StorageAdapter(
        bucket_name="custom-bucket",
        endpoint_url="http://localhost:9000",
        aws_access_key_id="mock-key-id",
        aws_secret_access_key="mock-secret-key",  # pragma: allowlist secret
        aws_session_token="mock-session-tok",
    )
    assert captured_kwargs["endpoint_url"] == "http://localhost:9000"
    assert captured_kwargs["aws_access_key_id"] == "mock-key-id"
    assert (
        captured_kwargs["aws_secret_access_key"]
        == "mock-secret-key"  # pragma: allowlist secret
    )
    assert captured_kwargs["aws_session_token"] == "mock-session-tok"


def test_s3_missing_dependency(monkeypatch: pytest.MonkeyPatch) -> None:
    """Verify MissingDependencyError when boto3 is not installed."""
    import sys

    monkeypatch.setitem(sys.modules, "boto3", None)
    with pytest.raises(MissingDependencyError, match="boto3"):
        s3_adapter.S3StorageAdapter(bucket_name="my-bucket")


@pytest.mark.anyio
async def test_async_s3_storage_adapter() -> None:
    """Verify asynchronous AsyncS3StorageAdapter operations."""
    client = MockS3Client()
    storage = s3_adapter.AsyncS3StorageAdapter(
        bucket_name="async-bucket", client=client
    )

    exists_init = await storage.exists_async("async.dat")
    assert exists_init is False

    res_put = await storage.put_async("async.dat", b"Async S3 bytes")
    assert res_put == "async.dat"

    exists_put = await storage.exists_async("async.dat")
    assert exists_put is True

    val = await storage.get_async("async.dat")
    assert val == b"Async S3 bytes"

    up_url = await storage.generate_presigned_upload_url_async(
        "async.dat", expires_in_seconds=600
    )
    assert "https://s3.amazonaws.com/async-bucket/async.dat" in up_url

    up_alias = await storage.generate_presigned_upload_url(
        "async.dat", expires_in_seconds=600
    )
    assert "https://s3.amazonaws.com/async-bucket/async.dat" in up_alias

    down_url = await storage.generate_presigned_download_url_async(
        "async.dat", expires_in_seconds=600
    )
    assert "https://s3.amazonaws.com/async-bucket/async.dat" in down_url

    down_alias = await storage.generate_presigned_download_url(
        "async.dat", expires_in_seconds=600
    )
    assert "https://s3.amazonaws.com/async-bucket/async.dat" in down_alias

    files = await storage.list_files_async()
    assert files == ["async.dat"]

    res_del = await storage.delete_async("async.dat")
    assert res_del is True
    exists_del = await storage.exists_async("async.dat")
    assert exists_del is False
