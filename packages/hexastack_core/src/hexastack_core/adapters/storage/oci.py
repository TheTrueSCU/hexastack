"""Oracle Cloud Infrastructure (OCI) Object Storage Adapters."""

from __future__ import annotations

import asyncio
import uuid
from datetime import UTC, datetime, timedelta
from typing import Any, BinaryIO

from hexastack_core.domain.exceptions import StorageError, StorageNotFoundError
from hexastack_core.ports.storage import (
    AsyncPresignedStoragePort,
    PresignedStoragePort,
)
from hexastack_core.utils.imports import require_dependency


class _ParDetails:
    """Internal container for Pre-Authenticated Request arguments."""

    def __init__(
        self,
        name: str,
        object_name: str,
        access_type: str,
        time_expires: datetime,
    ) -> None:
        self.name = name
        self.object_name = object_name
        self.access_type = access_type
        self.time_expires = time_expires


class OciStorageAdapter(PresignedStoragePort):
    """Oracle Cloud Infrastructure (OCI) Object Storage adapter.

    Notes/Architectural Intent:
        Implements synchronous OCI object storage operations and presigned URL
        generation via Pre-Authenticated Requests (PARs). Isolates the OCI Python
        SDK behind the optional hexastack-core[oci] package extra and supports
        injected mock clients for hermetic unit testing.
    """

    def __init__(
        self,
        bucket_name: str,
        namespace_name: str,
        client: Any = None,
        config: dict[str, Any] | None = None,
        signer: Any = None,
        region: str = "us-ashburn-1",
    ) -> None:
        """Initialize OCI storage adapter.

        Args:
            bucket_name: Target OCI Object Storage bucket name.
            namespace_name: OCI tenancy Object Storage namespace string.
            client: Optional pre-configured oci.object_storage.ObjectStorageClient instance.
            config: Optional OCI configuration dictionary.
            signer: Optional OCI authentication signer (e.g., InstancePrincipalsSigner).
            region: OCI region identifier (default 'us-ashburn-1').

        Raises:
            MissingDependencyError: If oci SDK is not installed and no client is provided.
        """
        self._bucket_name = bucket_name
        self._namespace_name = namespace_name
        self._region = region

        if client is not None:
            self._client = client
        else:
            oci_mod = require_dependency("oci", extra="oci", package="hexastack-core")
            cfg = config or {}
            self._client = oci_mod.object_storage.ObjectStorageClient(
                config=cfg,
                signer=signer,
            )

    def get(self, path: str) -> bytes:
        """Retrieve binary contents of an OCI stored object.

        Args:
            path: Relative object name/path within bucket.

        Returns:
            The raw byte content of the stored object.

        Raises:
            StorageNotFoundError: If object does not exist in bucket.
            StorageError: If retrieval fails.
        """
        try:
            res = self._client.get_object(self._namespace_name, self._bucket_name, path)
            data = getattr(res, "data", res)
            if hasattr(data, "content"):
                return bytes(data.content)
            if hasattr(data, "read"):
                return bytes(data.read())
            return bytes(data)
        except Exception as exc:
            err_str = str(exc)
            status = getattr(exc, "status", None)
            if status == 404 or "404" in err_str or "NotFound" in err_str:
                msg = f"OCI object not found: {path}"
                raise StorageNotFoundError(msg) from exc
            msg = f"Failed to retrieve OCI object {path}: {exc}"
            raise StorageError(msg) from exc

    def put(self, path: str, data: bytes | BinaryIO) -> str:
        """Persist data into OCI Object Storage at the given path.

        Args:
            path: Destination object name/path.
            data: Raw bytes or binary stream to persist.

        Returns:
            The canonical path of the stored object.

        Raises:
            StorageError: If persistence operation fails.
        """
        try:
            if isinstance(data, (bytes, bytearray)):
                body = bytes(data)
            elif hasattr(data, "read"):
                body = data
            else:
                msg = f"Unsupported data type for OCI storage: {type(data).__name__}"
                raise StorageError(msg)

            self._client.put_object(
                self._namespace_name,
                self._bucket_name,
                path,
                body,
            )
            return path
        except Exception as exc:
            if isinstance(exc, StorageError):
                raise
            msg = f"Failed to persist OCI object {path}: {exc}"
            raise StorageError(msg) from exc

    def delete(self, path: str) -> bool:
        """Delete an object from OCI Object Storage.

        Args:
            path: Object name/path to delete.

        Returns:
            True if deletion request succeeded.

        Raises:
            StorageError: If deletion fails.
        """
        try:
            self._client.delete_object(self._namespace_name, self._bucket_name, path)
            return True
        except Exception as exc:
            err_str = str(exc)
            status = getattr(exc, "status", None)
            if status == 404 or "404" in err_str or "NotFound" in err_str:
                return False
            msg = f"Failed to delete OCI object {path}: {exc}"
            raise StorageError(msg) from exc

    def exists(self, path: str) -> bool:
        """Check if an object exists in OCI Object Storage.

        Args:
            path: Object name/path to check.

        Returns:
            True if object exists, False otherwise.

        Raises:
            StorageError: If existence check encounters an unexpected error.
        """
        try:
            self._client.head_object(self._namespace_name, self._bucket_name, path)
            return True
        except Exception as exc:
            err_str = str(exc)
            status = getattr(exc, "status", None)
            if status == 404 or "404" in err_str or "NotFound" in err_str:
                return False
            msg = f"Failed to check OCI object existence {path}: {exc}"
            raise StorageError(msg) from exc

    def list_files(self, prefix: str = "") -> list[str]:
        """List object names matching prefix in OCI Object Storage bucket.

        Args:
            prefix: Optional object name prefix filter.

        Returns:
            List of matching object names sorted alphabetically.

        Raises:
            StorageError: If bucket listing fails.
        """
        try:
            kwargs: dict[str, Any] = {}
            if prefix:
                kwargs["prefix"] = prefix
            res = self._client.list_objects(
                self._namespace_name,
                self._bucket_name,
                **kwargs,
            )
            data = getattr(res, "data", res)
            objects = getattr(data, "objects", data)
            names: list[str] = []
            for item in objects:
                name = getattr(item, "name", str(item))
                names.append(name)
            return sorted(names)
        except Exception as exc:
            msg = f"Failed to list OCI objects with prefix {prefix}: {exc}"
            raise StorageError(msg) from exc

    def generate_presigned_upload_url(
        self,
        path: str,
        expires_in_seconds: int = 3600,
        content_type: str | None = None,
    ) -> str:
        """Generate a time-bounded presigned upload URL via OCI Pre-Authenticated Request.

        Args:
            path: Destination storage path or object name.
            expires_in_seconds: Token validity lifetime in seconds (default 3600).
            content_type: Optional expected MIME type.

        Returns:
            Preauthenticated upload URL string.

        Raises:
            StorageError: If PAR creation fails.
        """
        expires_at = datetime.now(UTC) + timedelta(seconds=expires_in_seconds)
        details = _ParDetails(
            name=f"par-upload-{uuid.uuid4().hex[:8]}",
            object_name=path,
            access_type="ObjectWrite",
            time_expires=expires_at,
        )
        try:
            res = self._client.create_preauthenticated_request(
                self._namespace_name,
                self._bucket_name,
                details,
            )
            data = getattr(res, "data", res)
            if hasattr(data, "full_path") and data.full_path:
                return str(data.full_path)
            access_uri = getattr(data, "access_uri", "")
            return f"https://objectstorage.{self._region}.oraclecloud.com{access_uri}"
        except Exception as exc:
            msg = f"Failed to generate OCI presigned upload URL for {path}: {exc}"
            raise StorageError(msg) from exc

    def generate_presigned_download_url(
        self,
        path: str,
        expires_in_seconds: int = 3600,
    ) -> str:
        """Generate a time-bounded presigned download URL via OCI Pre-Authenticated Request.

        Args:
            path: Target storage path or object name.
            expires_in_seconds: Token validity lifetime in seconds (default 3600).

        Returns:
            Preauthenticated download URL string.

        Raises:
            StorageError: If PAR creation fails.
        """
        expires_at = datetime.now(UTC) + timedelta(seconds=expires_in_seconds)
        details = _ParDetails(
            name=f"par-download-{uuid.uuid4().hex[:8]}",
            object_name=path,
            access_type="ObjectRead",
            time_expires=expires_at,
        )
        try:
            res = self._client.create_preauthenticated_request(
                self._namespace_name,
                self._bucket_name,
                details,
            )
            data = getattr(res, "data", res)
            if hasattr(data, "full_path") and data.full_path:
                return str(data.full_path)
            access_uri = getattr(data, "access_uri", "")
            return f"https://objectstorage.{self._region}.oraclecloud.com{access_uri}"
        except Exception as exc:
            msg = f"Failed to generate OCI presigned download URL for {path}: {exc}"
            raise StorageError(msg) from exc


class AsyncOciStorageAdapter(AsyncPresignedStoragePort):
    """Async wrapper around OciStorageAdapter executing non-blocking operations.

    Notes/Architectural Intent:
        Delegates synchronous OCI Object Storage SDK calls to a background threadpool
        via asyncio.to_thread, ensuring zero event-loop stalls.
    """

    def __init__(
        self,
        bucket_name: str,
        namespace_name: str,
        client: Any = None,
        config: dict[str, Any] | None = None,
        signer: Any = None,
        region: str = "us-ashburn-1",
        sync_storage: OciStorageAdapter | None = None,
    ) -> None:
        """Initialize async OCI storage adapter.

        Args:
            bucket_name: Target OCI Object Storage bucket name.
            namespace_name: OCI tenancy Object Storage namespace string.
            client: Optional pre-configured oci.object_storage.ObjectStorageClient instance.
            config: Optional OCI configuration dictionary.
            signer: Optional OCI authentication signer.
            region: OCI region identifier (default 'us-ashburn-1').
            sync_storage: Optional existing OciStorageAdapter instance.
        """
        self._sync = sync_storage or OciStorageAdapter(
            bucket_name=bucket_name,
            namespace_name=namespace_name,
            client=client,
            config=config,
            signer=signer,
            region=region,
        )

    async def get_async(self, path: str) -> bytes:
        """Retrieve binary contents of an OCI object asynchronously.

        Args:
            path: Object name in bucket.

        Returns:
            The raw byte content of the stored object.
        """
        return await asyncio.to_thread(self._sync.get, path)

    async def put_async(self, path: str, data: bytes | BinaryIO) -> str:
        """Persist data into OCI Object Storage asynchronously.

        Args:
            path: Destination object name.
            data: Raw bytes or binary stream to persist.

        Returns:
            The canonical path of the stored object.
        """
        return await asyncio.to_thread(self._sync.put, path, data)

    async def delete_async(self, path: str) -> bool:
        """Delete an object from OCI Object Storage asynchronously.

        Args:
            path: Object name to delete.

        Returns:
            True if deletion succeeded.
        """
        return await asyncio.to_thread(self._sync.delete, path)

    async def exists_async(self, path: str) -> bool:
        """Check if an object exists in OCI Object Storage asynchronously.

        Args:
            path: Object name to check.

        Returns:
            True if object exists, False otherwise.
        """
        return await asyncio.to_thread(self._sync.exists, path)

    async def list_files_async(self, prefix: str = "") -> list[str]:
        """List object names matching prefix asynchronously.

        Args:
            prefix: Optional object name prefix filter.

        Returns:
            List of matching object names sorted alphabetically.
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
            path: Destination storage path or object name.
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
            path: Target storage path or object name.
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
    "AsyncOciStorageAdapter",
    "OciStorageAdapter",
]
