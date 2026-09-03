"""Unit tests for FsspecStorageAdapter and AsyncFsspecStorageAdapter."""

from __future__ import annotations

import io
from typing import Any

import pytest

from hexastack_core.adapters.storage.fsspec import (
    AsyncFsspecStorageAdapter,
    FsspecStorageAdapter,
)
from hexastack_core.domain.exceptions import (
    MissingDependencyError,
    StorageError,
    StorageNotFoundError,
)


def test_fsspec_storage_memory_protocol() -> None:
    """Verify FsspecStorageAdapter with in-memory virtual filesystem."""
    storage = FsspecStorageAdapter(protocol="memory", base_path="mybucket")

    # Exists & Get non-existent
    assert storage.exists("obj1.dat") is False
    with pytest.raises(StorageNotFoundError):
        storage.get("obj1.dat")

    # Put bytes
    res = storage.put("obj1.dat", b"Virtual memory blob")
    assert res == "obj1.dat"
    assert storage.exists("obj1.dat") is True
    assert storage.get("obj1.dat") == b"Virtual memory blob"

    # Put stream
    stream = io.BytesIO(b"Stream data in memory")
    storage.put("sub/stream.dat", stream)
    assert storage.get("sub/stream.dat") == b"Stream data in memory"

    # Put stream
    txt_stream = io.BytesIO(b"Virtual text")
    storage.put("sub/text.txt", txt_stream)
    assert storage.get("sub/text.txt") == b"Virtual text"

    # Unsupported data type
    invalid_data: Any = 12345
    with pytest.raises(StorageError, match="Unsupported data type"):
        storage.put("sub/err.bin", invalid_data)

    # List files
    files = storage.list_files("")
    assert "obj1.dat" in files
    assert "sub/stream.dat" in files

    # Delete
    del1 = storage.delete("obj1.dat")
    assert del1 is True
    assert storage.exists("obj1.dat") is False
    del2 = storage.delete("obj1.dat")
    assert del2 is False


@pytest.mark.anyio
async def test_async_fsspec_storage_memory_protocol() -> None:
    """Verify AsyncFsspecStorageAdapter with memory protocol."""
    storage = AsyncFsspecStorageAdapter(protocol="memory", base_path="async_bucket")

    assert await storage.exists_async("async_blob.bin") is False
    with pytest.raises(StorageNotFoundError):
        await storage.get_async("async_blob.bin")

    await storage.put_async("async_blob.bin", b"Async virtual blob")
    assert await storage.exists_async("async_blob.bin") is True
    assert await storage.get_async("async_blob.bin") == b"Async virtual blob"

    files = await storage.list_files_async()
    assert "async_blob.bin" in files

    del_res = await storage.delete_async("async_blob.bin")
    assert del_res is True
    assert await storage.exists_async("async_blob.bin") is False


def test_fsspec_missing_dependency(monkeypatch: pytest.MonkeyPatch) -> None:
    """Verify MissingDependencyError when fsspec is not available."""
    import hexastack_core.adapters.storage.fsspec as fsspec_module

    monkeypatch.setattr(fsspec_module, "fsspec", None)
    with pytest.raises(MissingDependencyError, match="fsspec is required"):
        FsspecStorageAdapter(protocol="memory")
