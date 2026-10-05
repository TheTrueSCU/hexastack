"""Unit tests for StoragePort and AsyncStoragePort abstract contracts."""

from __future__ import annotations

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
