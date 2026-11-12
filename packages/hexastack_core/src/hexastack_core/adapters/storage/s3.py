"""Amazon S3 and S3-Compatible Object Storage Adapters."""

from __future__ import annotations

import asyncio
from typing import Any, BinaryIO

from hexastack_core.domain.exceptions import StorageError, StorageNotFoundError
from hexastack_core.ports.storage import (
    AsyncPresignedStoragePort,
    PresignedStoragePort,
)
from hexastack_core.utils.imports import require_dependency


class S3StorageAdapter(PresignedStoragePort):
    """Amazon S3 and S3-compatible (MinIO, Cloudflare R2, Ceph) storage adapter.

    Notes/Architectural Intent:
        Implements synchronous S3 object storage operations and presigned URL
        generation via boto3. Isolates AWS SDK dependencies behind the optional
        hexastack-core[s3] package extra and supports injected mock clients for
        hermetic unit testing.
    """

    def __init__(
        self,
        bucket_name: str,
        client: Any = None,
        region_name: str = "us-east-1",
        endpoint_url: str | None = None,
        aws_access_key_id: str | None = None,
        aws_secret_access_key: str | None = None,
        aws_session_token: str | None = None,
    ) -> None:
        """Initialize S3 storage adapter.

        Args:
            bucket_name: Target S3 bucket name.
            client: Optional pre-configured boto3 S3 client instance.
            region_name: AWS region identifier (default 'us-east-1').
            endpoint_url: Optional custom endpoint URI (e.g. for MinIO or localstack).
            aws_access_key_id: Optional AWS access key ID.
            aws_secret_access_key: Optional AWS secret access key.
            aws_session_token: Optional AWS session token for temporary credentials.

        Raises:
            MissingDependencyError: If boto3 is not installed and no client is provided.
        """
        self._bucket_name = bucket_name
        if client is not None:
            self._client = client
        else:
            boto3 = require_dependency("boto3", extra="s3", package="hexastack-core")
            client_kwargs: dict[str, Any] = {"region_name": region_name}
            if endpoint_url:
                client_kwargs["endpoint_url"] = endpoint_url
            if aws_access_key_id:
                client_kwargs["aws_access_key_id"] = aws_access_key_id
            if aws_secret_access_key:
                client_kwargs["aws_secret_access_key"] = aws_secret_access_key
            if aws_session_token:
                client_kwargs["aws_session_token"] = aws_session_token
            self._client = boto3.client("s3", **client_kwargs)

    def get(self, path: str) -> bytes:
        """Retrieve binary contents of an S3 object.

        Args:
            path: Object key in bucket.

        Returns:
            The raw byte content of the stored object.

        Raises:
            StorageNotFoundError: If object does not exist in bucket.
            StorageError: If retrieval fails.
        """
        try:
            response = self._client.get_object(Bucket=self._bucket_name, Key=path)
            body = response.get("Body")
            if hasattr(body, "read"):
                return body.read()
            return bytes(body)
        except Exception as exc:
            err_str = str(exc)
            code = ""
            if hasattr(exc, "response") and isinstance(exc.response, dict):
                code = exc.response.get("Error", {}).get("Code", "")
            if code in ("404", "NoSuchKey") or "NoSuchKey" in err_str:
                msg = f"S3 object not found: {path}"
                raise StorageNotFoundError(msg) from exc
            msg = f"Failed to retrieve S3 object {path}: {exc}"
            raise StorageError(msg) from exc

    def put(self, path: str, data: bytes | BinaryIO) -> str:
        """Persist data into S3 at the given path.

        Args:
            path: Destination object key.
            data: Raw bytes or binary stream to persist.

        Returns:
            The canonical path or key of the stored object.

        Raises:
            StorageError: If persistence operation fails.
        """
        try:
            if isinstance(data, (bytes, bytearray)):
                body = bytes(data)
            elif hasattr(data, "read"):
                content = data.read()
                if not isinstance(content, (bytes, bytearray)):
                    content = content.encode("utf-8")
                body = bytes(content)
            else:
                msg = f"Unsupported data type for S3 storage: {type(data).__name__}"
                raise StorageError(msg)

            self._client.put_object(
                Bucket=self._bucket_name,
                Key=path,
                Body=body,
            )
            return path
        except Exception as exc:
            if isinstance(exc, StorageError):
                raise
            msg = f"Failed to persist S3 object {path}: {exc}"
            raise StorageError(msg) from exc

    def delete(self, path: str) -> bool:
        """Delete an object from S3.

        Args:
            path: Object key to delete.

        Returns:
            True if deletion request succeeded.

        Raises:
            StorageError: If deletion fails.
        """
        try:
            self._client.delete_object(Bucket=self._bucket_name, Key=path)
            return True
        except Exception as exc:
            msg = f"Failed to delete S3 object {path}: {exc}"
            raise StorageError(msg) from exc

    def exists(self, path: str) -> bool:
        """Check if an object exists in S3.

        Args:
            path: Object key to check.

        Returns:
            True if object exists, False otherwise.

        Raises:
            StorageError: If existence check encounters an unexpected error.
        """
        try:
            self._client.head_object(Bucket=self._bucket_name, Key=path)
            return True
        except Exception as exc:
            err_str = str(exc)
            code = ""
            if hasattr(exc, "response") and isinstance(exc.response, dict):
                code = exc.response.get("Error", {}).get("Code", "")
            if (
                code in ("404", "NoSuchKey")
                or "404" in err_str
                or "NoSuchKey" in err_str
            ):
                return False
            msg = f"Failed to check S3 object existence {path}: {exc}"
            raise StorageError(msg) from exc

    def list_files(self, prefix: str = "") -> list[str]:
        """List object keys matching prefix in S3 bucket.

        Args:
            prefix: Optional path prefix filter.

        Returns:
            List of matching object keys sorted alphabetically.

        Raises:
            StorageError: If bucket listing fails.
        """
        results: list[str] = []
        kwargs: dict[str, Any] = {"Bucket": self._bucket_name}
        if prefix:
            kwargs["Prefix"] = prefix

        try:
            resp = self._client.list_objects_v2(**kwargs)
            for item in resp.get("Contents", []):
                if "Key" in item:
                    results.append(item["Key"])

            continuation_token = resp.get("NextContinuationToken")
            while continuation_token:
                kwargs["ContinuationToken"] = continuation_token
                resp = self._client.list_objects_v2(**kwargs)
                for item in resp.get("Contents", []):
                    if "Key" in item:
                        results.append(item["Key"])
                continuation_token = resp.get("NextContinuationToken")

            return sorted(results)
        except Exception as exc:
            msg = f"Failed to list S3 objects with prefix {prefix}: {exc}"
            raise StorageError(msg) from exc

    def generate_presigned_upload_url(
        self,
        path: str,
        expires_in_seconds: int = 3600,
        content_type: str | None = None,
    ) -> str:
        """Generate a time-bounded presigned upload URL for direct S3 object staging.

        Args:
            path: Destination storage path or key.
            expires_in_seconds: Token validity lifetime in seconds (default 3600).
            content_type: Optional expected MIME type.

        Returns:
            Preauthenticated upload URL string.

        Raises:
            StorageError: If presigned URL generation fails.
        """
        params: dict[str, Any] = {"Bucket": self._bucket_name, "Key": path}
        if content_type:
            params["ContentType"] = content_type
        try:
            url = self._client.generate_presigned_url(
                ClientMethod="put_object",
                Params=params,
                ExpiresIn=expires_in_seconds,
            )
            return str(url)
        except Exception as exc:
            msg = f"Failed to generate S3 presigned upload URL for {path}: {exc}"
            raise StorageError(msg) from exc

    def generate_presigned_download_url(
        self,
        path: str,
        expires_in_seconds: int = 3600,
    ) -> str:
        """Generate a time-bounded presigned download URL for direct S3 object retrieval.

        Args:
            path: Target storage path or key.
            expires_in_seconds: Token validity lifetime in seconds (default 3600).

        Returns:
            Preauthenticated download URL string.

        Raises:
            StorageError: If presigned URL generation fails.
        """
        params: dict[str, Any] = {"Bucket": self._bucket_name, "Key": path}
        try:
            url = self._client.generate_presigned_url(
                ClientMethod="get_object",
                Params=params,
                ExpiresIn=expires_in_seconds,
            )
            return str(url)
        except Exception as exc:
            msg = f"Failed to generate S3 presigned download URL for {path}: {exc}"
            raise StorageError(msg) from exc


class AsyncS3StorageAdapter(AsyncPresignedStoragePort):
    """Async wrapper around S3StorageAdapter executing non-blocking operations.

    Notes/Architectural Intent:
        Delegates S3 network operations and signature generation to worker threads
        via asyncio.to_thread, ensuring the event loop is not blocked during
        large blob transfers.
    """

    def __init__(
        self,
        bucket_name: str,
        client: Any = None,
        region_name: str = "us-east-1",
        endpoint_url: str | None = None,
        aws_access_key_id: str | None = None,
        aws_secret_access_key: str | None = None,
        aws_session_token: str | None = None,
        sync_storage: S3StorageAdapter | None = None,
    ) -> None:
        """Initialize async S3 storage adapter.

        Args:
            bucket_name: Target S3 bucket name.
            client: Optional pre-configured boto3 S3 client instance.
            region_name: AWS region identifier (default 'us-east-1').
            endpoint_url: Optional custom endpoint URI.
            aws_access_key_id: Optional AWS access key ID.
            aws_secret_access_key: Optional AWS secret access key.
            aws_session_token: Optional AWS session token.
            sync_storage: Optional existing S3StorageAdapter instance.
        """
        self._sync = sync_storage or S3StorageAdapter(
            bucket_name=bucket_name,
            client=client,
            region_name=region_name,
            endpoint_url=endpoint_url,
            aws_access_key_id=aws_access_key_id,
            aws_secret_access_key=aws_secret_access_key,
            aws_session_token=aws_session_token,
        )

    async def get_async(self, path: str) -> bytes:
        """Retrieve binary contents of an S3 object asynchronously.

        Args:
            path: Object key in bucket.

        Returns:
            The raw byte content of the stored object.
        """
        return await asyncio.to_thread(self._sync.get, path)

    async def put_async(self, path: str, data: bytes | BinaryIO) -> str:
        """Persist data into S3 asynchronously.

        Args:
            path: Destination object key.
            data: Raw bytes or binary stream to persist.

        Returns:
            The canonical path or key of the stored object.
        """
        return await asyncio.to_thread(self._sync.put, path, data)

    async def delete_async(self, path: str) -> bool:
        """Delete an object from S3 asynchronously.

        Args:
            path: Object key to delete.

        Returns:
            True if deletion succeeded.
        """
        return await asyncio.to_thread(self._sync.delete, path)

    async def exists_async(self, path: str) -> bool:
        """Check if an object exists in S3 asynchronously.

        Args:
            path: Object key to check.

        Returns:
            True if object exists, False otherwise.
        """
        return await asyncio.to_thread(self._sync.exists, path)

    async def list_files_async(self, prefix: str = "") -> list[str]:
        """List object keys matching prefix asynchronously.

        Args:
            prefix: Optional path prefix filter.

        Returns:
            List of matching object keys sorted alphabetically.
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
            path: Destination storage path or key.
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
            path: Target storage path or key.
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
    "AsyncS3StorageAdapter",
    "S3StorageAdapter",
]
