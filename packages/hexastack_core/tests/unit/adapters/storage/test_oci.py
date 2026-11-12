"""Unit tests for OciStorageAdapter and AsyncOciStorageAdapter."""

from __future__ import annotations

import io
from typing import Any

import pytest

from hexastack_core.adapters.storage import oci as oci_adapter
from hexastack_core.domain.exceptions import (
    MissingDependencyError,
    StorageError,
    StorageNotFoundError,
)


class MockOciResponse:
    """Mock response container simulating OCI SDK response structure."""

    def __init__(self, data: Any) -> None:
        self.data = data


class MockOciParData:
    """Mock preauthenticated request metadata."""

    def __init__(self, access_uri: str, full_path: str | None = None) -> None:
        self.access_uri = access_uri
        self.full_path = full_path


class MockOciObjectSummary:
    """Mock summary object for OCI list_objects response."""

    def __init__(self, name: str) -> None:
        self.name = name


class MockOciListObjectsData:
    """Mock container for list_objects objects list."""

    def __init__(self, objects: list[MockOciObjectSummary]) -> None:
        self.objects = objects


class MockOciServiceError(Exception):
    """Mock OCI service error with HTTP status code."""

    def __init__(self, message: str, status: int = 404) -> None:
        super().__init__(message)
        self.status = status


class MockOciClient:
    """Mock OCI ObjectStorageClient for hermetic testing."""

    def __init__(self) -> None:
        self.objects: dict[str, bytes] = {}

    def get_object(
        self, namespace_name: str, bucket_name: str, object_name: str
    ) -> MockOciResponse:
        if object_name not in self.objects:
            msg = f"NotFound: {object_name} in {bucket_name}"
            raise MockOciServiceError(msg, status=404)

        class ContentData:
            def __init__(self, content: bytes) -> None:
                self.content = content

        return MockOciResponse(ContentData(self.objects[object_name]))

    def put_object(
        self,
        namespace_name: str,
        bucket_name: str,
        object_name: str,
        put_object_body: bytes | Any,
    ) -> MockOciResponse:
        if isinstance(put_object_body, (bytes, bytearray)):
            self.objects[object_name] = bytes(put_object_body)
        elif hasattr(put_object_body, "read"):
            self.objects[object_name] = put_object_body.read()
        else:
            self.objects[object_name] = bytes(put_object_body)
        return MockOciResponse({"status": 200})

    def delete_object(
        self, namespace_name: str, bucket_name: str, object_name: str
    ) -> MockOciResponse:
        if object_name not in self.objects:
            raise MockOciServiceError(f"NotFound: {object_name}", status=404)
        del self.objects[object_name]
        return MockOciResponse({"status": 204})

    def head_object(
        self, namespace_name: str, bucket_name: str, object_name: str
    ) -> MockOciResponse:
        if object_name not in self.objects:
            raise MockOciServiceError(f"NotFound: {object_name}", status=404)
        return MockOciResponse({"content-length": len(self.objects[object_name])})

    def list_objects(
        self,
        namespace_name: str,
        bucket_name: str,
        prefix: str | None = None,
    ) -> MockOciResponse:
        pfx = prefix or ""
        matches = [
            MockOciObjectSummary(k)
            for k in sorted(self.objects.keys())
            if k.startswith(pfx)
        ]
        return MockOciResponse(MockOciListObjectsData(matches))

    def create_preauthenticated_request(
        self,
        namespace_name: str,
        bucket_name: str,
        create_preauthenticated_request_details: Any,
    ) -> MockOciResponse:
        obj = create_preauthenticated_request_details.object_name
        act = create_preauthenticated_request_details.access_type
        access_uri = (
            f"/p/token123/n/{namespace_name}/b/{bucket_name}/o/{obj}?action={act}"
        )
        return MockOciResponse(MockOciParData(access_uri=access_uri))


def test_oci_storage_adapter_crud_and_presigned() -> None:
    """Verify synchronous OciStorageAdapter operations with mock client."""
    client = MockOciClient()
    storage = oci_adapter.OciStorageAdapter(
        bucket_name="my-oci-bucket",
        namespace_name="my-tenancy",
        client=client,
        region="us-ashburn-1",
    )

    # Exists & Get non-existent
    exists_before = storage.exists("obj1.dat")
    assert exists_before is False
    with pytest.raises(StorageNotFoundError, match="OCI object not found"):
        storage.get("obj1.dat")

    # Put bytes
    res_put = storage.put("obj1.dat", b"OCI byte payload")
    assert res_put == "obj1.dat"
    exists_after = storage.exists("obj1.dat")
    assert exists_after is True
    val = storage.get("obj1.dat")
    assert val == b"OCI byte payload"

    # Put stream
    stream = io.BytesIO(b"OCI stream payload")
    res_stream = storage.put("sub/stream.dat", stream)
    assert res_stream == "sub/stream.dat"
    val_stream = storage.get("sub/stream.dat")
    assert val_stream == b"OCI stream payload"

    # Presigned URLs via PAR
    upload_url = storage.generate_presigned_upload_url(
        "sub/upload.tar.gz",
        expires_in_seconds=1800,
        content_type="application/gzip",
    )
    assert "https://objectstorage.us-ashburn-1.oraclecloud.com/p/token123" in upload_url
    assert "action=ObjectWrite" in upload_url

    download_url = storage.generate_presigned_download_url(
        "obj1.dat",
        expires_in_seconds=3600,
    )
    assert (
        "https://objectstorage.us-ashburn-1.oraclecloud.com/p/token123" in download_url
    )
    assert "action=ObjectRead" in download_url

    # List files
    files = storage.list_files("sub/")
    assert files == ["sub/stream.dat"]

    # Delete
    del_res = storage.delete("obj1.dat")
    assert del_res is True
    exists_del = storage.exists("obj1.dat")
    assert exists_del is False
    del_nonexistent = storage.delete("obj1.dat")
    assert del_nonexistent is False


def test_oci_storage_adapter_error_handling() -> None:
    """Verify OciStorageAdapter error wrapping."""

    class BrokenOciClient:
        def get_object(self, *args: Any, **kwargs: Any) -> Any:
            msg = "OCI network partition"
            raise ConnectionError(msg)

        def put_object(self, *args: Any, **kwargs: Any) -> Any:
            msg = "OCI quota exceeded"
            raise OSError(msg)

        def delete_object(self, *args: Any, **kwargs: Any) -> Any:
            msg = "Internal Error 500"
            raise RuntimeError(msg)

        def head_object(self, *args: Any, **kwargs: Any) -> Any:
            msg = "Auth failed 401"
            raise PermissionError(msg)

        def list_objects(self, *args: Any, **kwargs: Any) -> Any:
            msg = "List error"
            raise RuntimeError(msg)

        def create_preauthenticated_request(self, *args: Any, **kwargs: Any) -> Any:
            msg = "PAR error"
            raise RuntimeError(msg)

    storage = oci_adapter.OciStorageAdapter(
        bucket_name="broken",
        namespace_name="ns",
        client=BrokenOciClient(),
    )

    with pytest.raises(StorageError, match="Failed to retrieve OCI object"):
        storage.get("error.dat")

    with pytest.raises(StorageError, match="Failed to persist OCI object"):
        storage.put("error.dat", b"payload")

    with pytest.raises(StorageError, match="Failed to delete OCI object"):
        storage.delete("error.dat")

    with pytest.raises(StorageError, match="Failed to check OCI object existence"):
        storage.exists("error.dat")

    with pytest.raises(StorageError, match="Failed to list OCI objects"):
        storage.list_files()

    with pytest.raises(
        StorageError, match="Failed to generate OCI presigned upload URL"
    ):
        storage.generate_presigned_upload_url("error.dat")

    with pytest.raises(
        StorageError, match="Failed to generate OCI presigned download URL"
    ):
        storage.generate_presigned_download_url("error.dat")

    # Invalid data type
    invalid_data: Any = 5678
    storage_mock = oci_adapter.OciStorageAdapter(
        bucket_name="b", namespace_name="ns", client=MockOciClient()
    )
    with pytest.raises(StorageError, match="Unsupported data type"):
        storage_mock.put("err.dat", invalid_data)


def test_oci_init_kwargs(monkeypatch: pytest.MonkeyPatch) -> None:
    """Verify OciStorageAdapter client initialization with config and signer."""
    captured: dict[str, Any] = {}

    class FakeOciMod:
        class object_storage:
            class ObjectStorageClient:
                def __init__(self, config: dict[str, Any], signer: Any = None) -> None:
                    captured["config"] = config
                    captured["signer"] = signer

    monkeypatch.setattr(
        oci_adapter, "require_dependency", lambda *args, **kwargs: FakeOciMod
    )
    oci_adapter.OciStorageAdapter(
        bucket_name="my-bucket",
        namespace_name="my-ns",
        config={"region": "us-phoenix-1"},
        signer="my-signer",
    )
    assert captured["config"]["region"] == "us-phoenix-1"
    assert captured["signer"] == "my-signer"


def test_oci_missing_dependency(monkeypatch: pytest.MonkeyPatch) -> None:
    """Verify MissingDependencyError when oci is not installed."""
    import sys

    monkeypatch.setitem(sys.modules, "oci", None)
    with pytest.raises(MissingDependencyError, match="oci"):
        oci_adapter.OciStorageAdapter(bucket_name="b", namespace_name="ns")


@pytest.mark.anyio
async def test_async_oci_storage_adapter() -> None:
    """Verify asynchronous AsyncOciStorageAdapter operations."""
    client = MockOciClient()
    storage = oci_adapter.AsyncOciStorageAdapter(
        bucket_name="async-bucket",
        namespace_name="async-ns",
        client=client,
        region="us-ashburn-1",
    )

    exists_init = await storage.exists_async("async.dat")
    assert exists_init is False

    res_put = await storage.put_async("async.dat", b"Async OCI bytes")
    assert res_put == "async.dat"

    exists_put = await storage.exists_async("async.dat")
    assert exists_put is True

    val = await storage.get_async("async.dat")
    assert val == b"Async OCI bytes"

    up_url = await storage.generate_presigned_upload_url_async(
        "async.dat", expires_in_seconds=600
    )
    assert "https://objectstorage.us-ashburn-1.oraclecloud.com/p/token123" in up_url

    up_alias = await storage.generate_presigned_upload_url(
        "async.dat", expires_in_seconds=600
    )
    assert "https://objectstorage.us-ashburn-1.oraclecloud.com/p/token123" in up_alias

    down_url = await storage.generate_presigned_download_url_async(
        "async.dat", expires_in_seconds=600
    )
    assert "https://objectstorage.us-ashburn-1.oraclecloud.com/p/token123" in down_url

    down_alias = await storage.generate_presigned_download_url(
        "async.dat", expires_in_seconds=600
    )
    assert "https://objectstorage.us-ashburn-1.oraclecloud.com/p/token123" in down_alias

    files = await storage.list_files_async()
    assert files == ["async.dat"]

    res_del = await storage.delete_async("async.dat")
    assert res_del is True
    exists_del = await storage.exists_async("async.dat")
    assert exists_del is False
