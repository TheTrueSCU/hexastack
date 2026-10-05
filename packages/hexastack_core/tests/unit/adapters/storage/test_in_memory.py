"""Unit tests for InMemoryStorage and AsyncInMemoryStorage adapters."""

from __future__ import annotations

import io
from typing import Any, cast

import pytest

from hexastack_core.adapters.storage.in_memory import (
    AsyncInMemoryStorage,
    InMemoryStorage,
)
from hexastack_core.domain.exceptions import StorageError, StorageNotFoundError


def test_in_memory_storage_sync_lifecycle() -> None:
    """Verify synchronous in-memory storage operations."""
    storage = InMemoryStorage()

    # Exists & Get non-existent
    assert storage.exists("file.txt") is False
    with pytest.raises(
        StorageNotFoundError, match="Object not found in storage: file.txt"
    ):
        storage.get("file.txt")

    # Put raw bytes
    res_path = storage.put("docs/readme.txt", b"Hello Hexastack")
    assert res_path == "docs/readme.txt"
    assert storage.exists("docs/readme.txt") is True
    assert storage.get("docs/readme.txt") == b"Hello Hexastack"

    # Put file stream
    stream = io.BytesIO(b"Stream data")
    storage.put("docs/stream.bin", stream)
    assert storage.get("docs/stream.bin") == b"Stream data"

    # Put stream
    text_stream = io.BytesIO(b"Text stream")
    storage.put("docs/text.txt", text_stream)
    assert storage.get("docs/text.txt") == b"Text stream"

    # Put bytearray
    storage.put("docs/bytearray.bin", cast("Any", bytearray(b"bytearray payload")))
    assert storage.get("docs/bytearray.bin") == b"bytearray payload"

    # Put stream with str output
    class StringReader:
        def read(self):
            return "string content"

    storage.put("docs/str.txt", cast("Any", StringReader()))
    assert storage.get("docs/str.txt") == b"string content"

    # Put stream that raises
    class BrokenReader:
        def read(self):
            raise OSError("Disk read error")

    with pytest.raises(StorageError, match="Failed to persist object at docs/fail.bin"):
        storage.put("docs/fail.bin", cast("Any", BrokenReader()))

    # Unsupported data type
    invalid_data: Any = 12345
    with pytest.raises(StorageError, match="Unsupported data type for storage"):
        storage.put("invalid.dat", invalid_data)

    # List files with prefix
    files = storage.list_files("docs/")
    assert "docs/readme.txt" in files
    assert "docs/stream.bin" in files
    assert "docs/text.txt" in files
    assert "docs/bytearray.bin" in files
    assert "docs/str.txt" in files

    # Delete
    del1 = storage.delete("docs/readme.txt")
    assert del1 is True
    assert storage.exists("docs/readme.txt") is False
    del2 = storage.delete("docs/readme.txt")
    assert del2 is False

    # Clear
    storage.clear()
    assert storage.list_files() == []


@pytest.mark.anyio
async def test_async_in_memory_storage_lifecycle() -> None:
    """Verify asynchronous in-memory storage wrapper operations."""
    sync_inner = InMemoryStorage()
    storage = AsyncInMemoryStorage(sync_storage=sync_inner)

    assert await storage.exists_async("async_file.txt") is False
    with pytest.raises(StorageNotFoundError):
        await storage.get_async("async_file.txt")

    # Put bytes
    await storage.put_async("async_file.txt", b"Async payload")
    assert await storage.exists_async("async_file.txt") is True
    assert await storage.get_async("async_file.txt") == b"Async payload"

    # List & Delete
    files = await storage.list_files_async("async_")
    assert files == ["async_file.txt"]

    del_res = await storage.delete_async("async_file.txt")
    assert del_res is True
    assert await storage.exists_async("async_file.txt") is False

    await storage.put_async("k1", b"v1")
    await storage.clear_async()
    assert await storage.list_files_async() == []
