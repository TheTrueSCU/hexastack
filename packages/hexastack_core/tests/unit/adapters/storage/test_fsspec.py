"""Unit tests for FsspecStorageAdapter and AsyncFsspecStorageAdapter."""

from __future__ import annotations

import io
from typing import Any, cast

import pytest

from hexastack_core.adapters.storage import fsspec as fsspec_adapter
from hexastack_core.domain.exceptions import (
    MissingDependencyError,
    StorageError,
    StorageNotFoundError,
)


def test_fsspec_storage_memory_protocol() -> None:
    """Verify FsspecStorageAdapter with in-memory virtual filesystem."""
    storage = fsspec_adapter.FsspecStorageAdapter(
        protocol="memory", base_path="mybucket"
    )

    # Exists & Get non-existent
    assert storage.exists("obj1.dat") is False
    with pytest.raises(StorageNotFoundError):
        storage.get("obj1.dat")

    # Put bytes
    res = storage.put("obj1.dat", b"Virtual memory blob")
    assert res == "obj1.dat"
    assert storage.exists("obj1.dat") is True
    assert storage.get("obj1.dat") == b"Virtual memory blob"

    # Put bytearray
    storage.put("sub/bytearray.bin", cast("Any", bytearray(b"bytearray blob")))
    assert storage.get("sub/bytearray.bin") == b"bytearray blob"

    # Put stream
    stream = io.BytesIO(b"Stream data in memory")
    storage.put("sub/stream.dat", stream)
    assert storage.get("sub/stream.dat") == b"Stream data in memory"

    # Put stream with str
    class FsspecStrReader:
        def read(self):
            return "Virtual text"

    storage.put("sub/text.txt", cast("Any", FsspecStrReader()))
    assert storage.get("sub/text.txt") == b"Virtual text"

    # Unsupported data type
    invalid_data: Any = 12345
    with pytest.raises(StorageError, match="Unsupported data type"):
        storage.put("sub/err.bin", invalid_data)

    # List files
    files = storage.list_files("")
    assert "obj1.dat" in files
    assert "sub/stream.dat" in files
    assert "sub/bytearray.bin" in files
    assert "sub/text.txt" in files

    # Delete
    del1 = storage.delete("obj1.dat")
    assert del1 is True
    assert storage.exists("obj1.dat") is False
    del2 = storage.delete("obj1.dat")
    assert del2 is False


def test_fsspec_storage_custom_fs_and_errors() -> None:
    """Verify FsspecStorageAdapter with injected mock fs and error wrapping."""

    class MockFs:
        def exists(self, key):
            return True

        def open(self, key, mode):
            msg = "Read I/O failure"
            raise OSError(msg)

        def rm(self, key):
            msg = "Delete I/O failure"
            raise OSError(msg)

        def find(self, base):
            msg = "Find I/O failure"
            raise OSError(msg)

    storage = fsspec_adapter.FsspecStorageAdapter(fs=MockFs())
    assert storage.exists("anything") is True

    with pytest.raises(StorageError, match="Failed to read fsspec object"):
        storage.get("test.dat")

    with pytest.raises(StorageError, match="Failed to write fsspec object"):
        storage.put("test.dat", b"payload")

    with pytest.raises(StorageError, match="Failed to delete fsspec object"):
        storage.delete("test.dat")

    with pytest.raises(StorageError, match="Failed to list fsspec files"):
        storage.list_files()


@pytest.mark.anyio
async def test_async_fsspec_storage_memory_protocol() -> None:
    """Verify AsyncFsspecStorageAdapter with memory protocol."""
    storage = fsspec_adapter.AsyncFsspecStorageAdapter(
        protocol="memory", base_path="async_bucket"
    )

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
    import sys

    monkeypatch.setitem(sys.modules, "fsspec", None)
    monkeypatch.setattr(fsspec_adapter, "fsspec", None)
    with pytest.raises(MissingDependencyError, match="fsspec is required"):
        fsspec_adapter.FsspecStorageAdapter(protocol="memory")
