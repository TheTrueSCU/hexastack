"""Unit tests for StoragePort, AsyncStoragePort, and PresignedStoragePort abstract contracts."""

from __future__ import annotations

import inspect
from typing import BinaryIO

import pytest

from hexastack_core.adapters.storage import (
    AsyncInMemoryStorage,
    InMemoryStorage,
)
from hexastack_core.domain.exceptions import StorageError
from hexastack_core.ports.storage import (
    AsyncPresignedStoragePort,
    AsyncStoragePort,
    PresignedStoragePort,
    StoragePort,
)


def test_storage_port_subclass_instantiation() -> None:
    """Verify that concrete StoragePort subclass can be instantiated and invoked."""
    storage: StoragePort = InMemoryStorage()
    res_put = storage.put("test.txt", b"data")
    assert res_put == "test.txt"
    val = storage.get("test.txt")
    assert val == b"data"
    res_new = storage.put("test.txt", b"new")
    assert res_new == "test.txt"
    deleted = storage.delete("test.txt")
    assert deleted is True
    exists_flag = storage.exists("test.txt")
    assert exists_flag is False


@pytest.mark.anyio
async def test_async_storage_port_subclass_instantiation() -> None:
    """Verify that concrete AsyncStoragePort subclass can be instantiated and invoked."""
    storage: AsyncStoragePort = AsyncInMemoryStorage()
    res_put = await storage.put_async("async_test.txt", b"async_data")
    assert res_put == "async_test.txt"
    val = await storage.get_async("async_test.txt")
    assert val == b"async_data"
    res_new = await storage.put_async("async_test.txt", b"async_new")
    assert res_new == "async_test.txt"
    deleted = await storage.delete_async("async_test.txt")
    assert deleted is True
    exists_flag = await storage.exists_async("async_test.txt")
    assert exists_flag is False


def test_storage_port_is_abstract() -> None:
    """Verify that StoragePort cannot be instantiated directly and is abstract."""
    is_abs = inspect.isabstract(StoragePort)
    assert is_abs is True
    with pytest.raises(TypeError, match="Can't instantiate abstract class"):
        StoragePort()  # ty: ignore[call-non-callable] # type: ignore[abstract]


def test_storage_port_abstract_methods() -> None:
    """Verify abstract methods on StoragePort."""
    expected = {"delete", "exists", "get", "list_files", "put"}
    abstracts = StoragePort.__abstractmethods__
    diff = expected.difference(abstracts)
    assert len(diff) == 0


def test_storage_port_default_presigned_raises() -> None:
    """Verify that base StoragePort default presigned methods raise StorageError."""

    class DummyStorage(StoragePort):
        def get(self, path: str) -> bytes:
            return b""

        def put(self, path: str, data: bytes | BinaryIO) -> str:
            return path

        def delete(self, path: str) -> bool:
            return True

        def exists(self, path: str) -> bool:
            return True

        def list_files(self, prefix: str = "") -> list[str]:
            return []

    dummy = DummyStorage()
    with pytest.raises(
        StorageError, match="DummyStorage does not support presigned upload URLs"
    ):
        dummy.generate_presigned_upload_url("obj.dat")

    with pytest.raises(
        StorageError, match="DummyStorage does not support presigned download URLs"
    ):
        dummy.generate_presigned_download_url("obj.dat")


def test_presigned_storage_port_is_abstract() -> None:
    """Verify that PresignedStoragePort cannot be instantiated directly and requires presigned methods."""
    is_abs = inspect.isabstract(PresignedStoragePort)
    assert is_abs is True
    abstracts = PresignedStoragePort.__abstractmethods__
    assert "generate_presigned_upload_url" in abstracts
    assert "generate_presigned_download_url" in abstracts


def test_async_storage_port_is_abstract() -> None:
    """Verify that AsyncStoragePort cannot be instantiated directly and is abstract."""
    is_abs = inspect.isabstract(AsyncStoragePort)
    assert is_abs is True
    with pytest.raises(TypeError, match="Can't instantiate abstract class"):
        AsyncStoragePort()  # ty: ignore[call-non-callable] # type: ignore[abstract]


def test_async_storage_port_abstract_methods() -> None:
    """Verify abstract methods on AsyncStoragePort."""
    expected = {
        "delete_async",
        "exists_async",
        "get_async",
        "list_files_async",
        "put_async",
    }
    abstracts = AsyncStoragePort.__abstractmethods__
    diff = expected.difference(abstracts)
    assert len(diff) == 0


@pytest.mark.anyio
async def test_async_storage_port_default_presigned_raises() -> None:
    """Verify that base AsyncStoragePort default presigned methods raise StorageError."""

    class DummyAsyncStorage(AsyncStoragePort):
        async def get_async(self, path: str) -> bytes:
            return b""

        async def put_async(self, path: str, data: bytes | BinaryIO) -> str:
            return path

        async def delete_async(self, path: str) -> bool:
            return True

        async def exists_async(self, path: str) -> bool:
            return True

        async def list_files_async(self, prefix: str = "") -> list[str]:
            return []

    dummy = DummyAsyncStorage()
    with pytest.raises(
        StorageError, match="DummyAsyncStorage does not support presigned upload URLs"
    ):
        await dummy.generate_presigned_upload_url_async("obj.dat")

    with pytest.raises(
        StorageError, match="DummyAsyncStorage does not support presigned download URLs"
    ):
        await dummy.generate_presigned_download_url_async("obj.dat")

    with pytest.raises(
        StorageError, match="DummyAsyncStorage does not support presigned upload URLs"
    ):
        await dummy.generate_presigned_upload_url("obj.dat")

    with pytest.raises(
        StorageError, match="DummyAsyncStorage does not support presigned download URLs"
    ):
        await dummy.generate_presigned_download_url("obj.dat")


def test_async_presigned_storage_port_is_abstract() -> None:
    """Verify that AsyncPresignedStoragePort is abstract with async presigned methods."""
    is_abs = inspect.isabstract(AsyncPresignedStoragePort)
    assert is_abs is True
    abstracts = AsyncPresignedStoragePort.__abstractmethods__
    assert "generate_presigned_upload_url_async" in abstracts
    assert "generate_presigned_download_url_async" in abstracts
