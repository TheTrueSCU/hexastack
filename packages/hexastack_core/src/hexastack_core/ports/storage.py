from __future__ import annotations

from abc import ABC, abstractmethod
from typing import BinaryIO


class StoragePort(ABC):
    """Abstract port defining synchronous object and file storage operations.

    Notes/Architectural Intent:
        Decouples business domains, task orchestrators, and file-handling services
        from specific underlying storage engines (Local Filesystem, AWS S3, Google
        Cloud Storage, Azure Blob Storage, or Memory).
    """

    @abstractmethod
    def get(self, path: str) -> bytes:
        """Retrieve binary contents of a stored object.

        Args:
            path: Relative or absolute URI/key identifying the stored object.

        Returns:
            The raw byte content of the stored object.

        Raises:
            StorageNotFoundError: If the object does not exist.
            StorageError: If storage retrieval fails.
        """

    @abstractmethod
    def put(self, path: str, data: bytes | BinaryIO) -> str:
        """Persist data into storage at the given path.

        Args:
            path: Destination path or object key.
            data: Raw bytes or binary stream to persist.

        Returns:
            The canonical path or URI of the stored object.

        Raises:
            StorageError: If the persistence operation fails.
        """

    @abstractmethod
    def delete(self, path: str) -> bool:
        """Delete an object from storage.

        Args:
            path: Path or key of the object to delete.

        Returns:
            True if the object existed and was deleted, False otherwise.

        Raises:
            StorageError: If deletion fails due to permissions or connection issues.
        """

    @abstractmethod
    def exists(self, path: str) -> bool:
        """Check if an object exists in storage.

        Args:
            path: Path or key of the object to check.

        Returns:
            True if the object exists, False otherwise.

        Raises:
            StorageError: If existence check encounters an underlying error.
        """

    @abstractmethod
    def list_files(self, prefix: str = "") -> list[str]:
        """List object paths matching a prefix.

        Args:
            prefix: Optional path prefix to filter stored objects.

        Returns:
            List of object paths matching the prefix.

        Raises:
            StorageError: If directory or bucket listing fails.
        """


class AsyncStoragePort(ABC):
    """Abstract port defining asynchronous object and file storage operations.

    Notes/Architectural Intent:
        Async-native counterpart to StoragePort for non-blocking file streaming
        and cloud blob transfers in asyncio/FastAPI/gRPC event loops.
    """

    @abstractmethod
    async def get_async(self, path: str) -> bytes:
        """Retrieve binary contents of a stored object asynchronously.

        Args:
            path: Relative or absolute URI/key identifying the stored object.

        Returns:
            The raw byte content of the stored object.

        Raises:
            StorageNotFoundError: If the object does not exist.
            StorageError: If storage retrieval fails.
        """

    @abstractmethod
    async def put_async(self, path: str, data: bytes | BinaryIO) -> str:
        """Persist data into storage at the given path asynchronously.

        Args:
            path: Destination path or object key.
            data: Raw bytes or binary stream to persist.

        Returns:
            The canonical path or URI of the stored object.

        Raises:
            StorageError: If the persistence operation fails.
        """

    @abstractmethod
    async def delete_async(self, path: str) -> bool:
        """Delete an object from storage asynchronously.

        Args:
            path: Path or key of the object to delete.

        Returns:
            True if the object existed and was deleted, False otherwise.

        Raises:
            StorageError: If deletion fails due to permissions or connection issues.
        """

    @abstractmethod
    async def exists_async(self, path: str) -> bool:
        """Check if an object exists in storage asynchronously.

        Args:
            path: Path or key of the object to check.

        Returns:
            True if the object exists, False otherwise.

        Raises:
            StorageError: If existence check encounters an underlying error.
        """

    @abstractmethod
    async def list_files_async(self, prefix: str = "") -> list[str]:
        """List object paths matching a prefix asynchronously.

        Args:
            prefix: Optional path prefix to filter stored objects.

        Returns:
            List of object paths matching the prefix.

        Raises:
            StorageError: If directory or bucket listing fails.
        """


__all__ = [
    "AsyncStoragePort",
    "StoragePort",
]
