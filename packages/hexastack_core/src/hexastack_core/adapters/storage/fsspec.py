"""Unified fsspec Storage Adapters for Cloud and Virtual Filesystems."""

from __future__ import annotations

import asyncio
from typing import Any, BinaryIO

from hexastack_core.domain.exceptions import (
    MissingDependencyError,
    StorageError,
    StorageNotFoundError,
)
from hexastack_core.ports.storage import AsyncStoragePort, StoragePort

try:
    import fsspec
except ImportError:
    fsspec = None  # type: ignore[assignment]


class FsspecStorageAdapter(StoragePort):
    """Unified cloud and local storage adapter backed by fsspec.

    Notes/Architectural Intent:
        Wraps any fsspec-supported filesystem protocol (s3, gcs, abfs, memory, file)
        behind the standardized StoragePort interface. Requires fsspec extra
        (pip install hexastack-core[fsspec]).
    """

    def __init__(
        self,
        protocol: str = "file",
        base_path: str = "",
        storage_options: dict[str, Any] | None = None,
        fs: Any = None,
    ) -> None:
        """Initialize fsspec storage adapter.

        Args:
            protocol: URI scheme protocol (e.g. "s3", "gcs", "abfs", "memory", "file").
            base_path: Optional root path or bucket prefix.
            storage_options: Optional credentials and connection parameters passed to fsspec.
            fs: Optional pre-configured fsspec.AbstractFileSystem instance.

        Raises:
            MissingDependencyError: If fsspec is not installed.
        """
        self._protocol = protocol
        self._base_path = base_path.rstrip("/")
        self._options = storage_options or {}

        if fs is not None:
            self._fs = fs
        elif fsspec is not None:
            self._fs = fsspec.filesystem(self._protocol, **self._options)
        else:
            msg = "fsspec is required for FsspecStorageAdapter. Install via: pip install hexastack-core[fsspec]"
            raise MissingDependencyError(msg)

    def _resolve_key(self, path: str) -> str:
        """Resolve full URI or path key combining base path.

        Args:
            path: Relative path or key.

        Returns:
            Resolved full key string.
        """
        clean = path.lstrip("/")
        if self._base_path:
            return f"{self._base_path}/{clean}"
        return clean

    def get(self, path: str) -> bytes:
        """Retrieve binary contents of a stored object.

        Args:
            path: Object key.

        Returns:
            Raw bytes of the object.

        Raises:
            StorageNotFoundError: If the object does not exist.
            StorageError: If reading fails.
        """
        key = self._resolve_key(path)
        if not self._fs.exists(key):
            msg = f"Object not found in fsspec storage: {path}"
            raise StorageNotFoundError(msg)

        try:
            with self._fs.open(key, "rb") as f:
                return f.read()
        except Exception as exc:
            if isinstance(exc, StorageNotFoundError):
                raise
            msg = f"Failed to read fsspec object at {path}: {exc}"
            raise StorageError(msg) from exc

    def put(self, path: str, data: bytes | BinaryIO) -> str:
        """Persist data into fsspec filesystem.

        Args:
            path: Destination key.
            data: Raw bytes or binary stream.

        Returns:
            Canonical relative path.

        Raises:
            StorageError: If writing fails.
        """
        key = self._resolve_key(path)
        try:
            if isinstance(data, (bytes, bytearray)):
                raw_bytes = bytes(data)
            elif callable(getattr(data, "read", None)):
                content = data.read()
                if not isinstance(content, (bytes, bytearray)):
                    content = str(content).encode("utf-8")
                raw_bytes = bytes(content)
            else:
                msg = f"Unsupported data type for storage: {type(data).__name__}"
                raise StorageError(msg)

            with self._fs.open(key, "wb") as f:
                f.write(raw_bytes)
            return path
        except Exception as exc:
            if isinstance(exc, StorageError):
                raise
            msg = f"Failed to write fsspec object at {path}: {exc}"
            raise StorageError(msg) from exc

    def delete(self, path: str) -> bool:
        """Delete an object from fsspec storage.

        Args:
            path: Object key.

        Returns:
            True if object existed and was removed, False otherwise.

        Raises:
            StorageError: If deletion fails.
        """
        key = self._resolve_key(path)
        if not self._fs.exists(key):
            return False
        try:
            self._fs.rm(key)
            return True
        except Exception as exc:
            msg = f"Failed to delete fsspec object at {path}: {exc}"
            raise StorageError(msg) from exc

    def exists(self, path: str) -> bool:
        """Check if an object exists in fsspec storage.

        Args:
            path: Object key.

        Returns:
            True if object exists, False otherwise.
        """
        key = self._resolve_key(path)
        return bool(self._fs.exists(key))

    def list_files(self, prefix: str = "") -> list[str]:
        """List object keys matching prefix.

        Args:
            prefix: Optional path prefix filter.

        Returns:
            List of matching relative paths.

        Raises:
            StorageError: If listing fails.
        """
        search_target = self._resolve_key(prefix)
        try:
            if self._fs.exists(search_target) or self._base_path:
                items = self._fs.find(self._base_path or search_target)
            else:
                items = self._fs.find("")

            results: list[str] = []
            clean_base = self._base_path.lstrip("/")
            for item in items:
                rel = item.lstrip("/")
                if clean_base and rel.startswith(clean_base):
                    rel = rel[len(clean_base) :].lstrip("/")
                if rel.startswith(prefix.lstrip("/")):
                    results.append(rel)
            return sorted(results)
        except Exception as exc:
            msg = f"Failed to list fsspec files with prefix {prefix}: {exc}"
            raise StorageError(msg) from exc


class AsyncFsspecStorageAdapter(AsyncStoragePort):
    """Async wrapper around FsspecStorageAdapter offloading I/O to threadpool.

    Notes/Architectural Intent:
        Provides non-blocking async operations over fsspec cloud filesystems.
    """

    def __init__(
        self,
        protocol: str = "file",
        base_path: str = "",
        storage_options: dict[str, Any] | None = None,
        fs: Any = None,
    ) -> None:
        """Initialize async fsspec storage adapter.

        Args:
            protocol: URI scheme protocol.
            base_path: Optional root path or bucket prefix.
            storage_options: Optional parameters passed to fsspec.
            fs: Optional pre-configured filesystem instance.
        """
        self._sync = FsspecStorageAdapter(
            protocol=protocol,
            base_path=base_path,
            storage_options=storage_options,
            fs=fs,
        )

    async def get_async(self, path: str) -> bytes:
        """Retrieve binary contents of a stored object asynchronously.

        Args:
            path: Object key.

        Returns:
            Raw bytes of the object.
        """
        return await asyncio.to_thread(self._sync.get, path)

    async def put_async(self, path: str, data: bytes | BinaryIO) -> str:
        """Persist data into fsspec filesystem asynchronously.

        Args:
            path: Destination key.
            data: Raw bytes or binary stream.

        Returns:
            Canonical relative path.
        """
        return await asyncio.to_thread(self._sync.put, path, data)

    async def delete_async(self, path: str) -> bool:
        """Delete an object from fsspec storage asynchronously.

        Args:
            path: Object key.

        Returns:
            True if object was deleted, False otherwise.
        """
        return await asyncio.to_thread(self._sync.delete, path)

    async def exists_async(self, path: str) -> bool:
        """Check if an object exists in fsspec storage asynchronously.

        Args:
            path: Object key.

        Returns:
            True if object exists, False otherwise.
        """
        return await asyncio.to_thread(self._sync.exists, path)

    async def list_files_async(self, prefix: str = "") -> list[str]:
        """List object keys matching prefix asynchronously.

        Args:
            prefix: Optional path prefix filter.

        Returns:
            List of matching relative paths.
        """
        return await asyncio.to_thread(self._sync.list_files, prefix)


__all__ = [
    "AsyncFsspecStorageAdapter",
    "FsspecStorageAdapter",
]
