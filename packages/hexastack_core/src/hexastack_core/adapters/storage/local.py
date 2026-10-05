"""Local Filesystem Storage Adapters."""

from __future__ import annotations

import asyncio
from pathlib import Path
from typing import BinaryIO

from hexastack_core.domain.exceptions import StorageError, StorageNotFoundError
from hexastack_core.ports.storage import AsyncStoragePort, StoragePort


class LocalStorageAdapter(StoragePort):
    """Local filesystem storage adapter adhering to StoragePort.

    Notes/Architectural Intent:
        Stores objects as files under a dedicated root directory. Automatically
        creates nested parent directories upon write. Zero external dependencies.
    """

    def __init__(self, root_dir: str | Path = ".") -> None:
        """Initialize local storage adapter with base root directory.

        Args:
            root_dir: Root directory path where files are persisted.
        """
        self._root = Path(root_dir).resolve()
        self._root.mkdir(parents=True, exist_ok=True)

    def _resolve_path(self, path: str) -> Path:
        """Resolve a relative or absolute key to a safe path within root directory.

        Args:
            path: Relative or key path.

        Returns:
            Resolved Path object.
        """
        clean_path = path.lstrip("/")
        return self._root / clean_path

    def get(self, path: str) -> bytes:
        """Retrieve binary contents of a local file.

        Args:
            path: Relative file path.

        Returns:
            Raw bytes of the file.

        Raises:
            StorageNotFoundError: If file does not exist.
            StorageError: If reading fails.
        """
        target = self._resolve_path(path)
        if not target.is_file():
            msg = f"Local file not found: {path}"
            raise StorageNotFoundError(msg)

        try:
            return target.read_bytes()
        except Exception as exc:
            msg = f"Failed to read file {path}: {exc}"
            raise StorageError(msg) from exc

    def put(self, path: str, data: bytes | BinaryIO) -> str:
        """Persist data to local filesystem.

        Args:
            path: Relative destination path.
            data: Raw bytes or open binary file stream.

        Returns:
            Canonical relative path.

        Raises:
            StorageError: If writing to disk fails.
        """
        target = self._resolve_path(path)
        try:
            target.parent.mkdir(parents=True, exist_ok=True)
            if isinstance(data, (bytes, bytearray)):
                target.write_bytes(bytes(data))
            elif hasattr(data, "read"):
                content = data.read()
                if not isinstance(content, (bytes, bytearray)):
                    content = content.encode("utf-8")
                target.write_bytes(bytes(content))
            else:
                msg = f"Unsupported data type for storage: {type(data).__name__}"
                raise StorageError(msg)
            return path
        except Exception as exc:
            if isinstance(exc, StorageError):
                raise
            msg = f"Failed to write file {path}: {exc}"
            raise StorageError(msg) from exc

    def delete(self, path: str) -> bool:
        """Delete a local file.

        Args:
            path: Relative file path.

        Returns:
            True if file existed and was removed, False if it did not exist.

        Raises:
            StorageError: If deletion fails due to OS errors.
        """
        target = self._resolve_path(path)
        if not target.exists():
            return False
        try:
            target.unlink()
            return True
        except Exception as exc:
            msg = f"Failed to delete file {path}: {exc}"
            raise StorageError(msg) from exc

    def exists(self, path: str) -> bool:
        """Check if a local file exists.

        Args:
            path: Relative file path.

        Returns:
            True if file exists and is a regular file, False otherwise.
        """
        target = self._resolve_path(path)
        return target.is_file()

    def list_files(self, prefix: str = "") -> list[str]:
        """List relative file paths matching prefix.

        Args:
            prefix: Optional path prefix filter.

        Returns:
            List of matching relative file paths sorted alphabetically.
        """
        results: list[str] = []
        try:
            for item in self._root.rglob("*"):
                if item.is_file():
                    rel = item.relative_to(self._root).as_posix()
                    if rel.startswith(prefix):
                        results.append(rel)
            return sorted(results)
        except Exception as exc:
            msg = f"Failed to list files with prefix {prefix}: {exc}"
            raise StorageError(msg) from exc


class AsyncLocalStorageAdapter(AsyncStoragePort):
    """Async wrapper around LocalStorageAdapter offloading I/O to threadpool.

    Notes/Architectural Intent:
        Wraps blocking filesystem operations via asyncio.to_thread for non-blocking
        execution in async coroutines.
    """

    def __init__(self, root_dir: str | Path = ".") -> None:
        """Initialize async local storage adapter.

        Args:
            root_dir: Root directory path.
        """
        self._sync = LocalStorageAdapter(root_dir=root_dir)

    async def get_async(self, path: str) -> bytes:
        """Retrieve binary contents of a local file asynchronously.

        Args:
            path: Relative file path.

        Returns:
            Raw bytes of the file.
        """
        return await asyncio.to_thread(self._sync.get, path)

    async def put_async(self, path: str, data: bytes | BinaryIO) -> str:
        """Persist data to local filesystem asynchronously.

        Args:
            path: Relative destination path.
            data: Raw bytes or binary stream.

        Returns:
            Canonical relative path.
        """
        return await asyncio.to_thread(self._sync.put, path, data)

    async def delete_async(self, path: str) -> bool:
        """Delete a local file asynchronously.

        Args:
            path: Relative file path.

        Returns:
            True if file existed and was removed, False otherwise.
        """
        return await asyncio.to_thread(self._sync.delete, path)

    async def exists_async(self, path: str) -> bool:
        """Check if a local file exists asynchronously.

        Args:
            path: Relative file path.

        Returns:
            True if file exists, False otherwise.
        """
        return await asyncio.to_thread(self._sync.exists, path)

    async def list_files_async(self, prefix: str = "") -> list[str]:
        """List relative file paths matching prefix asynchronously.

        Args:
            prefix: Optional path prefix filter.

        Returns:
            List of matching relative paths.
        """
        return await asyncio.to_thread(self._sync.list_files, prefix)


__all__ = [
    "AsyncLocalStorageAdapter",
    "LocalStorageAdapter",
]
