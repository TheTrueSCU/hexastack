"""Unit tests for StoragePort and AsyncStoragePort abstract contracts."""

from __future__ import annotations

import inspect

import pytest

from hexastack_core.adapters.storage import (
    AsyncInMemoryStorage,
    InMemoryStorage,
)
from hexastack_core.ports.storage import AsyncStoragePort, StoragePort


def test_storage_port_subclass_instantiation() -> None:
    """Verify that concrete StoragePort subclass can be instantiated and invoked."""
    storage: StoragePort = InMemoryStorage()
    storage.put("test.txt", b"data")
    assert storage.get("test.txt") == b"data"
    assert storage.put("test.txt", b"new") == "test.txt"
    deleted = storage.delete("test.txt")
    assert deleted is True
    assert storage.exists("test.txt") is False


@pytest.mark.anyio
async def test_async_storage_port_subclass_instantiation() -> None:
    """Verify that concrete AsyncStoragePort subclass can be instantiated and invoked."""
    storage: AsyncStoragePort = AsyncInMemoryStorage()
    await storage.put_async("async_test.txt", b"async_data")
    assert await storage.get_async("async_test.txt") == b"async_data"
    assert await storage.put_async("async_test.txt", b"async_new") == "async_test.txt"
    deleted = await storage.delete_async("async_test.txt")
    assert deleted is True
    assert await storage.exists_async("async_test.txt") is False


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
