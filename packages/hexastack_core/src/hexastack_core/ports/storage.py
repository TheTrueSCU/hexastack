from __future__ import annotations

from abc import ABC, abstractmethod
from typing import BinaryIO

from hexastack_core.domain.exceptions import StorageError


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

    def generate_presigned_upload_url(
        self,
        path: str,
        expires_in_seconds: int = 3600,
        content_type: str | None = None,
    ) -> str:
        """Generate a time-bounded presigned upload URL for direct object staging.

        Args:
            path: Destination storage path or key.
            expires_in_seconds: Token validity lifetime in seconds (default 3600).
            content_type: Optional expected MIME type.

        Returns:
            Preauthenticated upload URL string.

        Raises:
            StorageError: If the storage backend does not support presigned URLs or generation fails.
        """
        msg = f"{type(self).__name__} does not support presigned upload URLs"
        raise StorageError(msg)

    def generate_presigned_download_url(
        self,
        path: str,
        expires_in_seconds: int = 3600,
    ) -> str:
        """Generate a time-bounded presigned download URL for direct object retrieval.

        Args:
            path: Target storage path or key.
            expires_in_seconds: Token validity lifetime in seconds (default 3600).

        Returns:
            Preauthenticated download URL string.

        Raises:
            StorageError: If the storage backend does not support presigned URLs or generation fails.
        """
        msg = f"{type(self).__name__} does not support presigned download URLs"
        raise StorageError(msg)


class PresignedStoragePort(StoragePort):
    """Abstract port for storage backends with mandatory presigned URL generation.

    Notes/Architectural Intent:
        Enforces implementation of presigned URL generation for high-throughput
        data-plane stages that bypass the application server.
    """

    @abstractmethod
    def generate_presigned_upload_url(
        self,
        path: str,
        expires_in_seconds: int = 3600,
        content_type: str | None = None,
    ) -> str:
        """Generate a time-bounded presigned upload URL for direct object staging.

        Args:
            path: Destination storage path or key.
            expires_in_seconds: Token validity lifetime in seconds (default 3600).
            content_type: Optional expected MIME type.

        Returns:
            Preauthenticated upload URL string.

        Raises:
            StorageError: If presigned URL generation fails.
        """

    @abstractmethod
    def generate_presigned_download_url(
        self,
        path: str,
        expires_in_seconds: int = 3600,
    ) -> str:
        """Generate a time-bounded presigned download URL for direct object retrieval.

        Args:
            path: Target storage path or key.
            expires_in_seconds: Token validity lifetime in seconds (default 3600).

        Returns:
            Preauthenticated download URL string.

        Raises:
            StorageError: If presigned URL generation fails.
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

    async def generate_presigned_upload_url_async(
        self,
        path: str,
        expires_in_seconds: int = 3600,
        content_type: str | None = None,
    ) -> str:
        """Generate a time-bounded presigned upload URL asynchronously.

        Args:
            path: Destination storage path or key.
            expires_in_seconds: Token validity lifetime in seconds (default 3600).
            content_type: Optional expected MIME type.

        Returns:
            Preauthenticated upload URL string.

        Raises:
            StorageError: If the storage backend does not support presigned URLs or generation fails.
        """
        msg = f"{type(self).__name__} does not support presigned upload URLs"
        raise StorageError(msg)

    async def generate_presigned_download_url_async(
        self,
        path: str,
        expires_in_seconds: int = 3600,
    ) -> str:
        """Generate a time-bounded presigned download URL asynchronously.

        Args:
            path: Target storage path or key.
            expires_in_seconds: Token validity lifetime in seconds (default 3600).

        Returns:
            Preauthenticated download URL string.

        Raises:
            StorageError: If the storage backend does not support presigned URLs or generation fails.
        """
        msg = f"{type(self).__name__} does not support presigned download URLs"
        raise StorageError(msg)

    async def generate_presigned_upload_url(
        self,
        path: str,
        expires_in_seconds: int = 3600,
        content_type: str | None = None,
    ) -> str:
        """Generate a time-bounded presigned upload URL asynchronously.

        Args:
            path: Destination storage path or key.
            expires_in_seconds: Token validity lifetime in seconds (default 3600).
            content_type: Optional expected MIME type.

        Returns:
            Preauthenticated upload URL string.

        Raises:
            StorageError: If the storage backend does not support presigned URLs or generation fails.
        """
        return await self.generate_presigned_upload_url_async(
            path, expires_in_seconds=expires_in_seconds, content_type=content_type
        )

    async def generate_presigned_download_url(
        self,
        path: str,
        expires_in_seconds: int = 3600,
    ) -> str:
        """Generate a time-bounded presigned download URL asynchronously.

        Args:
            path: Target storage path or key.
            expires_in_seconds: Token validity lifetime in seconds (default 3600).

        Returns:
            Preauthenticated download URL string.

        Raises:
            StorageError: If the storage backend does not support presigned URLs or generation fails.
        """
        return await self.generate_presigned_download_url_async(
            path, expires_in_seconds=expires_in_seconds
        )


class AsyncPresignedStoragePort(AsyncStoragePort):
    """Abstract port for asynchronous storage backends with mandatory presigned URL generation.

    Notes/Architectural Intent:
        Enforces asynchronous implementation of presigned URL generation for
        high-throughput non-blocking data staging.
    """

    @abstractmethod
    async def generate_presigned_upload_url_async(
        self,
        path: str,
        expires_in_seconds: int = 3600,
        content_type: str | None = None,
    ) -> str:
        """Generate a time-bounded presigned upload URL asynchronously.

        Args:
            path: Destination storage path or key.
            expires_in_seconds: Token validity lifetime in seconds (default 3600).
            content_type: Optional expected MIME type.

        Returns:
            Preauthenticated upload URL string.

        Raises:
            StorageError: If presigned URL generation fails.
        """

    @abstractmethod
    async def generate_presigned_download_url_async(
        self,
        path: str,
        expires_in_seconds: int = 3600,
    ) -> str:
        """Generate a time-bounded presigned download URL asynchronously.

        Args:
            path: Target storage path or key.
            expires_in_seconds: Token validity lifetime in seconds (default 3600).

        Returns:
            Preauthenticated download URL string.

        Raises:
            StorageError: If presigned URL generation fails.
        """


__all__ = [
    "AsyncPresignedStoragePort",
    "AsyncStoragePort",
    "PresignedStoragePort",
    "StoragePort",
]
