"""In-Memory Object and File Storage Adapters."""

from __future__ import annotations

import hashlib
import hmac
import threading
from typing import BinaryIO

from hexastack_core.domain.exceptions import StorageError, StorageNotFoundError
from hexastack_core.ports.storage import (
    AsyncPresignedStoragePort,
    PresignedStoragePort,
)


class InMemoryStorage(PresignedStoragePort):
    """Thread-safe in-memory object storage adapter.

    Notes/Architectural Intent:
        Stores objects as raw bytes in an in-memory dictionary guarded by a reentrant lock.
        Ideal for fast, zero-I/O unit tests and ephemeral local pipelines.
    """

    def __init__(self) -> None:
        """Initialize in-memory storage dictionary and synchronization lock."""
        self._data: dict[str, bytes] = {}
        self._lock = threading.RLock()

    def get(self, path: str) -> bytes:
        """Retrieve binary contents of a stored object.

        Args:
            path: Object key to retrieve.

        Returns:
            The raw byte content of the stored object.

        Raises:
            StorageNotFoundError: If path does not exist in storage.
        """
        with self._lock:
            if path not in self._data:
                msg = f"Object not found in storage: {path}"
                raise StorageNotFoundError(msg)
            return self._data[path]

    def put(self, path: str, data: bytes | BinaryIO) -> str:
        """Persist data into in-memory storage.

        Args:
            path: Destination key.
            data: Raw bytes or binary stream to persist.

        Returns:
            The stored object path.

        Raises:
            StorageError: If reading stream or storing bytes fails.
        """
        try:
            if isinstance(data, (bytes, bytearray)):
                content = bytes(data)
            elif hasattr(data, "read"):
                content = data.read()
                if not isinstance(content, (bytes, bytearray)):
                    content = content.encode("utf-8")
                content = bytes(content)
            else:
                msg = f"Unsupported data type for storage: {type(data).__name__}"
                raise StorageError(msg)

            with self._lock:
                self._data[path] = content
            return path
        except Exception as exc:
            if isinstance(exc, StorageError):
                raise
            msg = f"Failed to persist object at {path}: {exc}"
            raise StorageError(msg) from exc

    def delete(self, path: str) -> bool:
        """Delete an object from in-memory storage.

        Args:
            path: Object key to delete.

        Returns:
            True if the object was deleted, False if it did not exist.
        """
        with self._lock:
            if path in self._data:
                del self._data[path]
                return True
            return False

    def exists(self, path: str) -> bool:
        """Check if an object exists in in-memory storage.

        Args:
            path: Object key to check.

        Returns:
            True if object is present, False otherwise.
        """
        with self._lock:
            return path in self._data

    def list_files(self, prefix: str = "") -> list[str]:
        """List object keys matching prefix.

        Args:
            prefix: Optional path prefix filter.

        Returns:
            List of matching object keys sorted alphabetically.
        """
        with self._lock:
            return sorted(k for k in self._data if k.startswith(prefix))

    def clear(self) -> None:
        """Clear all stored objects."""
        with self._lock:
            self._data.clear()

    def generate_presigned_upload_url(
        self,
        path: str,
        expires_in_seconds: int = 3600,
        content_type: str | None = None,
    ) -> str:
        """Generate a time-bounded presigned upload URL for in-memory staging.

        Args:
            path: Target storage path or object key.
            expires_in_seconds: Token validity duration in seconds (default 3600).
            content_type: Optional expected MIME type.

        Returns:
            Simulated presigned upload URL string.
        """
        token = hmac.new(
            b"in-memory-storage-key",
            f"upload:{path}:{expires_in_seconds}".encode(),
            hashlib.sha256,
        ).hexdigest()[:16]
        ct_param = f"&content_type={content_type}" if content_type else ""
        return f"memory://staging/{path}?action=upload&expires_in={expires_in_seconds}&token={token}{ct_param}"

    def generate_presigned_download_url(
        self,
        path: str,
        expires_in_seconds: int = 3600,
    ) -> str:
        """Generate a time-bounded presigned download URL for in-memory retrieval.

        Args:
            path: Target storage path or object key.
            expires_in_seconds: Token validity duration in seconds (default 3600).

        Returns:
            Simulated presigned download URL string.
        """
        token = hmac.new(
            b"in-memory-storage-key",
            f"download:{path}:{expires_in_seconds}".encode(),
            hashlib.sha256,
        ).hexdigest()[:16]
        return f"memory://staging/{path}?action=download&expires_in={expires_in_seconds}&token={token}"


class AsyncInMemoryStorage(AsyncPresignedStoragePort):
    """Async wrapper around InMemoryStorage.

    Notes/Architectural Intent:
        Delegates in-memory storage operations directly for async event loops.
    """

    def __init__(self, sync_storage: InMemoryStorage | None = None) -> None:
        """Initialize async in-memory storage.

        Args:
            sync_storage: Optional existing InMemoryStorage instance.
        """
        self._sync = sync_storage or InMemoryStorage()

    async def get_async(self, path: str) -> bytes:
        """Retrieve binary contents of a stored object asynchronously.

        Args:
            path: Object key to retrieve.

        Returns:
            The raw byte content of the stored object.

        Raises:
            StorageNotFoundError: If path does not exist.
        """
        return self._sync.get(path)

    async def put_async(self, path: str, data: bytes | BinaryIO) -> str:
        """Persist data into in-memory storage asynchronously.

        Args:
            path: Destination key.
            data: Raw bytes or binary stream to persist.

        Returns:
            The stored object path.
        """
        return self._sync.put(path, data)

    async def delete_async(self, path: str) -> bool:
        """Delete an object from in-memory storage asynchronously.

        Args:
            path: Object key to delete.

        Returns:
            True if the object was deleted, False otherwise.
        """
        return self._sync.delete(path)

    async def exists_async(self, path: str) -> bool:
        """Check if an object exists in in-memory storage asynchronously.

        Args:
            path: Object key to check.

        Returns:
            True if object is present, False otherwise.
        """
        return self._sync.exists(path)

    async def list_files_async(self, prefix: str = "") -> list[str]:
        """List object keys matching prefix asynchronously.

        Args:
            prefix: Optional path prefix filter.

        Returns:
            List of matching object keys.
        """
        return self._sync.list_files(prefix)

    async def clear_async(self) -> None:
        """Clear all stored objects asynchronously."""
        self._sync.clear()

    async def generate_presigned_upload_url_async(
        self,
        path: str,
        expires_in_seconds: int = 3600,
        content_type: str | None = None,
    ) -> str:
        """Generate a time-bounded presigned upload URL asynchronously.

        Args:
            path: Target storage path or object key.
            expires_in_seconds: Token validity duration in seconds (default 3600).
            content_type: Optional expected MIME type.

        Returns:
            Simulated presigned upload URL string.
        """
        return self._sync.generate_presigned_upload_url(
            path, expires_in_seconds=expires_in_seconds, content_type=content_type
        )

    async def generate_presigned_download_url_async(
        self,
        path: str,
        expires_in_seconds: int = 3600,
    ) -> str:
        """Generate a time-bounded presigned download URL asynchronously.

        Args:
            path: Target storage path or object key.
            expires_in_seconds: Token validity duration in seconds (default 3600).

        Returns:
            Simulated presigned download URL string.
        """
        return self._sync.generate_presigned_download_url(
            path, expires_in_seconds=expires_in_seconds
        )


__all__ = [
    "AsyncInMemoryStorage",
    "InMemoryStorage",
]
