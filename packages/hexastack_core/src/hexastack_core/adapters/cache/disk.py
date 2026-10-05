import json
import sqlite3
import tempfile
import time
from pathlib import Path
from typing import Any

from hexastack_core.ports.cache import AsyncCachePort, CachePort
from hexastack_core.ports.clock import ClockPort


class DiskCacheAdapter(CachePort):
    """Persistent L2 query and key-value cache adapter backed by SQLite.

    Notes/Architectural Intent:
        Implements CachePort using Python standard library `sqlite3` on local filesystem storage.
        Eliminates external dependencies and unsafe deserialization vulnerabilities (such as CVE-2025-69872).
        Enables multi-process safe cache sharing, persistent caching across service restarts,
        and offline CLI response caching without Redis or network dependencies. Accepts an
        optional ClockPort for deterministic simulation and property-based oracle testing.
    """

    def __init__(
        self,
        directory: str | Path | None = None,
        size_limit: int = 1_073_741_824,  # 1GB default
        clock: ClockPort | None = None,
    ) -> None:
        """Initialize DiskCacheAdapter.

        Args:
            directory: Filesystem path to cache database directory or db file. If None, creates a tempdir.
            size_limit: Maximum cache size in bytes (retained for API compatibility).
            clock: Optional ClockPort instance for deterministic time measurement.
        """
        self._size_limit = size_limit
        self._clock = clock
        if directory is None:
            self._directory = Path(tempfile.mkdtemp(prefix="hexastack_cache_"))
            self._db_path = self._directory / "cache.db"
        else:
            path = Path(directory)
            if path.is_dir() or not path.suffix:
                self._directory = path
                self._directory.mkdir(parents=True, exist_ok=True)
                self._db_path = self._directory / "cache.db"
            else:
                self._directory = path.parent
                self._directory.mkdir(parents=True, exist_ok=True)
                self._db_path = path

        self._conn = sqlite3.connect(
            str(self._db_path),
            timeout=30.0,
            check_same_thread=False,
            isolation_level=None,  # autocommit mode
        )
        self._init_db()

    def _init_db(self) -> None:
        """Initialize SQLite cache table schema and index."""
        with self._conn:
            self._conn.execute(
                """
                CREATE TABLE IF NOT EXISTS cache_entries (
                    key TEXT PRIMARY KEY,
                    value TEXT NOT NULL,
                    expires_at REAL
                )
                """
            )
            self._conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_expires_at ON cache_entries(expires_at)"
            )

    def _now(self) -> float:
        return self._clock.timestamp() if self._clock else time.time()

    def clear(self) -> None:
        """Clear all entries from the disk cache."""
        with self._conn:
            self._conn.execute("DELETE FROM cache_entries")

    def delete(self, key: str) -> bool:
        """Delete a key from disk cache.

        Args:
            key: Cache key to remove.

        Returns:
            True if key was deleted, False if not present.
        """
        with self._conn:
            cursor = self._conn.execute(
                "DELETE FROM cache_entries WHERE key = ?", (key,)
            )
            return cursor.rowcount > 0

    def get(self, key: str, default: Any = None) -> Any:
        """Retrieve a cached value by key.

        Args:
            key: Cache key identifier.
            default: Default fallback if missing or expired.

        Returns:
            Cached value or default.
        """
        now = self._now()
        cursor = self._conn.execute(
            "SELECT value, expires_at FROM cache_entries WHERE key = ?", (key,)
        )
        row = cursor.fetchone()
        if row is None:
            return default

        raw_val, expires_at = row
        if expires_at is not None and now > expires_at:
            self.delete(key)
            return default

        try:
            return json.loads(raw_val)
        except (json.JSONDecodeError, TypeError):
            return default

    def has(self, key: str) -> bool:
        """Check if a key is present and unexpired.

        Args:
            key: Cache key identifier.

        Returns:
            True if present, False otherwise.
        """
        return self.get(key, default=None) is not None

    def set(self, key: str, value: Any, ttl_seconds: float | None = None) -> None:
        """Store a key-value pair with optional TTL expiration in seconds.

        Args:
            key: Cache key identifier.
            value: Value object to persist (JSON serializable).
            ttl_seconds: Time to live in seconds.
        """
        now = self._now()
        expires_at = (now + ttl_seconds) if ttl_seconds is not None else None
        serialized = json.dumps(value)
        with self._conn:
            self._conn.execute(
                """
                INSERT INTO cache_entries (key, value, expires_at)
                VALUES (?, ?, ?)
                ON CONFLICT(key) DO UPDATE SET
                    value = excluded.value,
                    expires_at = excluded.expires_at
                """,
                (key, serialized, expires_at),
            )
        self._enforce_size_limit()

    def _enforce_size_limit(self) -> None:
        """Evict expired or oldest entries if cache payload size exceeds size_limit."""
        if self._size_limit is None or self._size_limit <= 0:
            return
        now = self._now()
        with self._conn:
            self._conn.execute(
                "DELETE FROM cache_entries WHERE expires_at IS NOT NULL AND expires_at < ?",
                (now,),
            )
            cursor = self._conn.execute(
                "SELECT COALESCE(SUM(LENGTH(key) + LENGTH(value)), 0) FROM cache_entries"
            )
            current_size = cursor.fetchone()[0]

            while current_size > self._size_limit:
                del_cursor = self._conn.execute(
                    "DELETE FROM cache_entries WHERE key IN ("
                    "SELECT key FROM cache_entries ORDER BY rowid ASC LIMIT 10"
                    ")"
                )
                if del_cursor.rowcount == 0:
                    break
                cursor = self._conn.execute(
                    "SELECT COALESCE(SUM(LENGTH(key) + LENGTH(value)), 0) FROM cache_entries"
                )
                current_size = cursor.fetchone()[0]

    def close(self) -> None:
        """Close underlying SQLite database handles."""
        self._conn.close()


class AsyncDiskCacheAdapter(AsyncCachePort):
    """Asynchronous persistent L2 query and key-value cache adapter backed by SQLite.

    Notes/Architectural Intent:
        Async counterpart to DiskCacheAdapter, offloading blocking disk I/O to the threadpool
        via `asyncio.to_thread`.
    """

    def __init__(
        self,
        directory: str | Path | None = None,
        size_limit: int = 1_073_741_824,
        clock: ClockPort | None = None,
    ) -> None:
        """Initialize AsyncDiskCacheAdapter.

        Args:
            directory: Directory path for diskcache.
            size_limit: Maximum cache size in bytes.
            clock: Optional ClockPort instance for deterministic time measurement.
        """
        self._sync_adapter = DiskCacheAdapter(
            directory=directory, size_limit=size_limit, clock=clock
        )

    async def clear_async(self) -> None:
        """Clear all entries asynchronously."""
        import asyncio

        await asyncio.to_thread(self._sync_adapter.clear)

    async def delete_async(self, key: str) -> bool:
        """Delete a key asynchronously."""
        import asyncio

        return await asyncio.to_thread(self._sync_adapter.delete, key)

    async def get_async(self, key: str, default: Any = None) -> Any:
        """Retrieve a cached value asynchronously."""
        import asyncio

        return await asyncio.to_thread(self._sync_adapter.get, key, default)

    async def has_async(self, key: str) -> bool:
        """Check if a key exists asynchronously."""
        import asyncio

        return await asyncio.to_thread(self._sync_adapter.has, key)

    async def set_async(
        self, key: str, value: Any, ttl_seconds: float | None = None
    ) -> None:
        """Store a key-value pair asynchronously."""
        import asyncio

        await asyncio.to_thread(self._sync_adapter.set, key, value, ttl_seconds)

    async def close_async(self) -> None:
        """Close cache handles asynchronously."""
        import asyncio

        await asyncio.to_thread(self._sync_adapter.close)


__all__ = [
    "AsyncDiskCacheAdapter",
    "DiskCacheAdapter",
]
