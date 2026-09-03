"""Unit tests for InMemoryStorage and AsyncInMemoryStorage adapters."""

from __future__ import annotations

import io
from typing import Any

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

    # Unsupported data type
    invalid_data: Any = 12345
    with pytest.raises(StorageError, match="Unsupported data type for storage"):
        storage.put("invalid.dat", invalid_data)

    # List files with prefix
    files = storage.list_files("docs/")
    assert files == ["docs/readme.txt", "docs/stream.bin", "docs/text.txt"]

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
    storage = AsyncInMemoryStorage()

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
