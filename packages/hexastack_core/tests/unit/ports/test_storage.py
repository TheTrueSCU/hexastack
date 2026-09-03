"""Unit tests for StoragePort and AsyncStoragePort abstract contracts."""

from __future__ import annotations

from typing import BinaryIO

import pytest

from hexastack_core.ports.storage import AsyncStoragePort, StoragePort


class DummySyncStorage(StoragePort):
    """Concrete dummy implementation to verify abstract method compliance."""

    def get(self, path: str) -> bytes:
        return b"data"

    def put(self, path: str, data: bytes | BinaryIO) -> str:
        return path

    def delete(self, path: str) -> bool:
        return True

    def exists(self, path: str) -> bool:
        return True

    def list_files(self, prefix: str = "") -> list[str]:
        return [f"{prefix}item.txt"]


class DummyAsyncStorage(AsyncStoragePort):
    """Concrete dummy implementation to verify async abstract method compliance."""

    async def get_async(self, path: str) -> bytes:
        return b"async_data"

    async def put_async(self, path: str, data: bytes | BinaryIO) -> str:
        return path

    async def delete_async(self, path: str) -> bool:
        return True

    async def exists_async(self, path: str) -> bool:
        return True

    async def list_files_async(self, prefix: str = "") -> list[str]:
        return [f"{prefix}async_item.txt"]


def test_storage_port_subclass_instantiation() -> None:
    """Verify that concrete StoragePort subclass can be instantiated and invoked."""
    storage = DummySyncStorage()
    assert storage.get("test.txt") == b"data"
    assert storage.put("test.txt", b"new") == "test.txt"
    deleted = storage.delete("test.txt")
    assert deleted is True
    assert storage.exists("test.txt") is True
    assert storage.list_files("prefix/") == ["prefix/item.txt"]


@pytest.mark.anyio
async def test_async_storage_port_subclass_instantiation() -> None:
    """Verify that concrete AsyncStoragePort subclass can be instantiated and invoked."""
    storage = DummyAsyncStorage()
    assert await storage.get_async("test.txt") == b"async_data"
    assert await storage.put_async("test.txt", b"new") == "test.txt"
    deleted = await storage.delete_async("test.txt")
    assert deleted is True
    assert await storage.exists_async("test.txt") is True
    assert await storage.list_files_async("prefix/") == ["prefix/async_item.txt"]
