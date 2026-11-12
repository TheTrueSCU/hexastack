"""Google Cloud Storage (GCS) Adapters."""

from __future__ import annotations

import asyncio
from datetime import timedelta
from typing import Any, BinaryIO

from hexastack_core.domain.exceptions import StorageError, StorageNotFoundError
from hexastack_core.ports.storage import (
    AsyncPresignedStoragePort,
    PresignedStoragePort,
)
from hexastack_core.utils.imports import require_dependency


class GcsStorageAdapter(PresignedStoragePort):
    """Google Cloud Storage (GCS) adapter with v4 signed URL generation.

    Notes/Architectural Intent:
        Implements synchronous GCS blob operations and presigned URL generation
        via the official google-cloud-storage SDK. Isolates cloud dependencies
        behind the optional hexastack-core[gcs] package extra and supports
        injected mock clients for hermetic unit testing.
    """

    def __init__(
        self,
        bucket_name: str,
        client: Any = None,
        project: str | None = None,
        credentials: Any = None,
    ) -> None:
        """Initialize GCS storage adapter.

        Args:
            bucket_name: Target GCS bucket name.
            client: Optional pre-configured google.cloud.storage.Client instance.
            project: Optional Google Cloud project ID.
            credentials: Optional Google Cloud credentials object.

        Raises:
            MissingDependencyError: If google-cloud-storage is not installed and no client is provided.
        """
        self._bucket_name = bucket_name
        if client is not None:
            self._client = client
        else:
            storage_mod = require_dependency(
                "google.cloud.storage", extra="gcs", package="hexastack-core"
            )
            self._client = storage_mod.Client(project=project, credentials=credentials)

    def _get_bucket(self) -> Any:
        """Retrieve bucket handle from client."""
        return self._client.bucket(self._bucket_name)

    def get(self, path: str) -> bytes:
        """Retrieve binary contents of a GCS blob.

        Args:
            path: Relative blob path within bucket.

        Returns:
            The raw byte content of the stored blob.

        Raises:
            StorageNotFoundError: If blob does not exist in bucket.
            StorageError: If retrieval fails.
        """
        try:
            bucket = self._get_bucket()
            blob = bucket.blob(path)
            if not blob.exists():
                msg = f"GCS blob not found: {path}"
                raise StorageNotFoundError(msg)
            return blob.download_as_bytes()
        except Exception as exc:
            if isinstance(exc, (StorageError, StorageNotFoundError)):
                raise
            msg = f"Failed to retrieve GCS blob {path}: {exc}"
            raise StorageError(msg) from exc

    def put(self, path: str, data: bytes | BinaryIO) -> str:
        """Persist data into GCS at the given path.

        Args:
            path: Destination blob path.
            data: Raw bytes or binary stream to persist.

        Returns:
            The canonical path of the stored blob.

        Raises:
            StorageError: If persistence operation fails.
        """
        try:
            bucket = self._get_bucket()
            blob = bucket.blob(path)
            if isinstance(data, (bytes, bytearray)):
                blob.upload_from_string(bytes(data))
            elif hasattr(data, "read"):
                blob.upload_from_file(data)
            else:
                msg = f"Unsupported data type for GCS storage: {type(data).__name__}"
                raise StorageError(msg)
            return path
        except Exception as exc:
            if isinstance(exc, StorageError):
                raise
            msg = f"Failed to persist GCS blob {path}: {exc}"
            raise StorageError(msg) from exc

    def delete(self, path: str) -> bool:
        """Delete a blob from GCS.

        Args:
            path: Blob path to delete.

        Returns:
            True if blob existed and was deleted, False otherwise.

        Raises:
            StorageError: If deletion fails.
        """
        try:
            bucket = self._get_bucket()
            blob = bucket.blob(path)
            if not blob.exists():
                return False
            blob.delete()
            return True
        except Exception as exc:
            msg = f"Failed to delete GCS blob {path}: {exc}"
            raise StorageError(msg) from exc

    def exists(self, path: str) -> bool:
        """Check if a blob exists in GCS.

        Args:
            path: Blob path to check.

        Returns:
            True if blob exists, False otherwise.

        Raises:
            StorageError: If existence check fails.
        """
        try:
            bucket = self._get_bucket()
            blob = bucket.blob(path)
            return bool(blob.exists())
        except Exception as exc:
            msg = f"Failed to check GCS blob existence {path}: {exc}"
            raise StorageError(msg) from exc

    def list_files(self, prefix: str = "") -> list[str]:
        """List blob names matching prefix in GCS bucket.

        Args:
            prefix: Optional path prefix filter.

        Returns:
            List of matching blob paths sorted alphabetically.

        Raises:
            StorageError: If bucket listing fails.
        """
        try:
            bucket = self._get_bucket()
            blobs = bucket.list_blobs(prefix=prefix or None)
            return sorted(b.name for b in blobs)
        except Exception as exc:
            msg = f"Failed to list GCS blobs with prefix {prefix}: {exc}"
            raise StorageError(msg) from exc

    def generate_presigned_upload_url(
        self,
        path: str,
        expires_in_seconds: int = 3600,
        content_type: str | None = None,
    ) -> str:
        """Generate a time-bounded presigned upload URL for direct GCS blob staging.

        Args:
            path: Destination blob path.
            expires_in_seconds: Token validity lifetime in seconds (default 3600).
            content_type: Optional expected MIME type.

        Returns:
            Preauthenticated upload URL string.

        Raises:
            StorageError: If signed URL generation fails.
        """
        try:
            bucket = self._get_bucket()
            blob = bucket.blob(path)
            kwargs: dict[str, Any] = {
                "version": "v4",
                "expiration": timedelta(seconds=expires_in_seconds),
                "method": "PUT",
            }
            if content_type:
                kwargs["content_type"] = content_type
            url = blob.generate_signed_url(**kwargs)
            return str(url)
        except Exception as exc:
            msg = f"Failed to generate GCS presigned upload URL for {path}: {exc}"
            raise StorageError(msg) from exc

    def generate_presigned_download_url(
        self,
        path: str,
        expires_in_seconds: int = 3600,
    ) -> str:
        """Generate a time-bounded presigned download URL for direct GCS blob retrieval.

        Args:
            path: Target blob path.
            expires_in_seconds: Token validity lifetime in seconds (default 3600).

        Returns:
            Preauthenticated download URL string.

        Raises:
            StorageError: If signed URL generation fails.
        """
        try:
            bucket = self._get_bucket()
            blob = bucket.blob(path)
            url = blob.generate_signed_url(
                version="v4",
                expiration=timedelta(seconds=expires_in_seconds),
                method="GET",
            )
            return str(url)
        except Exception as exc:
            msg = f"Failed to generate GCS presigned download URL for {path}: {exc}"
            raise StorageError(msg) from exc


class AsyncGcsStorageAdapter(AsyncPresignedStoragePort):
    """Async wrapper around GcsStorageAdapter executing non-blocking operations.

    Notes/Architectural Intent:
        Wraps synchronous GCS client calls via asyncio.to_thread for seamless
        integration into async event loops.
    """

    def __init__(
        self,
        bucket_name: str,
        client: Any = None,
        project: str | None = None,
        credentials: Any = None,
        sync_storage: GcsStorageAdapter | None = None,
    ) -> None:
        """Initialize async GCS storage adapter.

        Args:
            bucket_name: Target GCS bucket name.
            client: Optional pre-configured google.cloud.storage.Client instance.
            project: Optional Google Cloud project ID.
            credentials: Optional Google Cloud credentials object.
            sync_storage: Optional existing GcsStorageAdapter instance.
        """
        self._sync = sync_storage or GcsStorageAdapter(
            bucket_name=bucket_name,
            client=client,
            project=project,
            credentials=credentials,
        )

    async def get_async(self, path: str) -> bytes:
        """Retrieve binary contents of a GCS blob asynchronously.

        Args:
            path: Blob path in bucket.

        Returns:
            The raw byte content of the stored blob.
        """
        return await asyncio.to_thread(self._sync.get, path)

    async def put_async(self, path: str, data: bytes | BinaryIO) -> str:
        """Persist data into GCS asynchronously.

        Args:
            path: Destination blob path.
            data: Raw bytes or binary stream to persist.

        Returns:
            The canonical path of the stored blob.
        """
        return await asyncio.to_thread(self._sync.put, path, data)

    async def delete_async(self, path: str) -> bool:
        """Delete a blob from GCS asynchronously.

        Args:
            path: Blob path to delete.

        Returns:
            True if blob was deleted, False otherwise.
        """
        return await asyncio.to_thread(self._sync.delete, path)

    async def exists_async(self, path: str) -> bool:
        """Check if a blob exists in GCS asynchronously.

        Args:
            path: Blob path to check.

        Returns:
            True if blob exists, False otherwise.
        """
        return await asyncio.to_thread(self._sync.exists, path)

    async def list_files_async(self, prefix: str = "") -> list[str]:
        """List blob names matching prefix asynchronously.

        Args:
            prefix: Optional path prefix filter.

        Returns:
            List of matching blob paths sorted alphabetically.
        """
        return await asyncio.to_thread(self._sync.list_files, prefix)

    async def generate_presigned_upload_url_async(
        self,
        path: str,
        expires_in_seconds: int = 3600,
        content_type: str | None = None,
    ) -> str:
        """Generate a time-bounded presigned upload URL asynchronously.

        Args:
            path: Destination blob path.
            expires_in_seconds: Token validity lifetime in seconds (default 3600).
            content_type: Optional expected MIME type.

        Returns:
            Preauthenticated upload URL string.
        """
        return await asyncio.to_thread(
            self._sync.generate_presigned_upload_url,
            path,
            expires_in_seconds=expires_in_seconds,
            content_type=content_type,
        )

    async def generate_presigned_download_url_async(
        self,
        path: str,
        expires_in_seconds: int = 3600,
    ) -> str:
        """Generate a time-bounded presigned download URL asynchronously.

        Args:
            path: Target blob path.
            expires_in_seconds: Token validity lifetime in seconds (default 3600).

        Returns:
            Preauthenticated download URL string.
        """
        return await asyncio.to_thread(
            self._sync.generate_presigned_download_url,
            path,
            expires_in_seconds=expires_in_seconds,
        )


__all__ = [
    "AsyncGcsStorageAdapter",
    "GcsStorageAdapter",
]
