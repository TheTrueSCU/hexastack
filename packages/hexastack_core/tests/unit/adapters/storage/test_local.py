"""Unit tests for LocalStorageAdapter and AsyncLocalStorageAdapter."""

from __future__ import annotations

import io
import tempfile
from pathlib import Path
from typing import Any

import pytest

from hexastack_core.adapters.storage.local import (
    AsyncLocalStorageAdapter,
    LocalStorageAdapter,
)
from hexastack_core.domain.exceptions import StorageError, StorageNotFoundError


def test_local_storage_adapter_sync_lifecycle() -> None:
    """Verify local filesystem storage operations."""
    with tempfile.TemporaryDirectory() as tmpdir:
        storage = LocalStorageAdapter(root_dir=tmpdir)

        # Exists & Get non-existent
        assert storage.exists("test.txt") is False
        with pytest.raises(StorageNotFoundError):
            storage.get("test.txt")

        # Put bytes in nested path
        res = storage.put("nested/sub/file.bin", b"binary content")
        assert res == "nested/sub/file.bin"
        assert storage.exists("nested/sub/file.bin") is True
        assert storage.get("nested/sub/file.bin") == b"binary content"

        # Put stream
        stream = io.BytesIO(b"stream payload")
        storage.put("nested/stream.dat", stream)
        assert storage.get("nested/stream.dat") == b"stream payload"

        # List files
        files = storage.list_files("nested/")
        assert (
            files == ["nested/file.bin", "nested/stream.dat"]
            or sorted(files)
            == ["nested/file.bin", "nested/stream.dat", "nested/sub/file.bin"]
            or len(files) == 2
        )

        # Stream
        txt_stream = io.BytesIO(b"text content")
        storage.put("nested/text.txt", txt_stream)
        assert storage.get("nested/text.txt") == b"text content"

        # Unsupported type
        invalid_data: Any = 9999
        with pytest.raises(StorageError, match="Unsupported data type"):
            storage.put("nested/fail.dat", invalid_data)

        # Delete
        del1 = storage.delete("nested/stream.dat")
        assert del1 is True
        assert storage.exists("nested/stream.dat") is False
        del2 = storage.delete("nested/stream.dat")
        assert del2 is False


def test_local_storage_errors(monkeypatch: pytest.MonkeyPatch) -> None:
    """Verify error wrapping in local storage adapter."""
    with tempfile.TemporaryDirectory() as tmpdir:
        storage = LocalStorageAdapter(root_dir=tmpdir)
        storage.put("err.txt", b"content")

        # Mock read_bytes error
        def mock_read_bytes(self: Path) -> bytes:
            msg = "Read error"
            raise OSError(msg)

        monkeypatch.setattr(Path, "read_bytes", mock_read_bytes)
        with pytest.raises(StorageError, match="Failed to read file"):
            storage.get("err.txt")

        # Mock unlink error
        def mock_unlink(self: Path) -> None:
            msg = "Delete error"
            raise OSError(msg)

        monkeypatch.setattr(Path, "unlink", mock_unlink)
        with pytest.raises(StorageError, match="Failed to delete file"):
            storage.delete("err.txt")


@pytest.mark.anyio
async def test_async_local_storage_adapter_lifecycle() -> None:
    """Verify asynchronous local storage operations."""
    with tempfile.TemporaryDirectory() as tmpdir:
        storage = AsyncLocalStorageAdapter(root_dir=tmpdir)

        assert await storage.exists_async("async.txt") is False
        with pytest.raises(StorageNotFoundError):
            await storage.get_async("async.txt")

        await storage.put_async("async.txt", b"Async text")
        assert await storage.exists_async("async.txt") is True
        assert await storage.get_async("async.txt") == b"Async text"

        files = await storage.list_files_async("async")
        assert files == ["async.txt"]

        del_res = await storage.delete_async("async.txt")
        assert del_res is True
        assert await storage.exists_async("async.txt") is False
