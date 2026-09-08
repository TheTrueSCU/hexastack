from os import PathLike
from pathlib import Path
from typing import Any

from hexastack_core.domain.exceptions import LockError, MissingDependencyError
from hexastack_core.ports.lock import AsyncLockPort, LockPort


class FileLockAdapter(LockPort):
    """Inter-process filesystem mutual exclusion lock adapter.

    Notes/Architectural Intent:
        Implements LockPort using the `filelock` OS kernel flock/fcntl/LockFile primitive.
        Provides robust inter-process mutual exclusion across multiple worker processes,
        SQLite-backed Transactional Outbox pollers, and local CLI tools without requiring
        an external Redis or Postgres instance.
    """

    def __init__(
        self,
        lock_path: str | PathLike[str] | Path,
        timeout: float = 10.0,
    ) -> None:
        """Initialize FileLockAdapter.

        Args:
            lock_path: File path on disk for the lockfile (e.g. `/var/run/outbox.lock`).
            timeout: Default timeout in seconds for lock acquisition.

        Raises:
            MissingDependencyError: If `filelock` is not installed.
        """
        try:
            import filelock
        except ImportError as e:
            raise MissingDependencyError(
                "The 'filelock' package is required to use FileLockAdapter. "
                "Install it with: pip install hexastack-core[filelock] or hexastack-events[filelock]"
            ) from e

        self._path = Path(lock_path)
        self._default_timeout = timeout
        self._lock: Any = filelock.FileLock(str(self._path))

    def acquire(self, blocking: bool = True, timeout: float = -1.0) -> bool:
        """Acquire the file lock across processes.

        Args:
            blocking: Whether to block waiting for the lock.
            timeout: Maximum seconds to wait if blocking. Negative numbers use default timeout
                or block indefinitely.

        Returns:
            True if acquired, False otherwise.
        """
        if not blocking:
            effective_timeout = 0.0
        elif timeout >= 0:
            effective_timeout = timeout
        else:
            effective_timeout = self._default_timeout

        try:
            self._lock.acquire(timeout=effective_timeout, poll_interval=0.05)
            return True
        except TimeoutError:
            return False
        except Exception as exc:
            # Check for filelock Timeout exception name across versions
            if exc.__class__.__name__ == "Timeout":
                return False
            raise LockError(
                f"Failed to acquire file lock at {self._path}: {exc}"
            ) from exc

    def release(self) -> None:
        """Release the file lock.

        Raises:
            LockError: If the lock was not held or release fails.
        """
        try:
            self._lock.release(force=True)
        except Exception as exc:
            raise LockError(
                f"Failed to release file lock at {self._path}: {exc}"
            ) from exc

    def locked(self) -> bool:
        """Check if the file lock is held by the current process.

        Returns:
            True if held, False otherwise.
        """
        return self._lock.is_locked


class AsyncFileLockAdapter(AsyncLockPort):
    """Asynchronous inter-process filesystem mutual exclusion lock adapter.

    Notes/Architectural Intent:
        Async counterpart to FileLockAdapter offloading blocking kernel filelock operations
        to the asyncio threadpool executor (`asyncio.to_thread`) to prevent blocking the
        event loop.
    """

    def __init__(
        self,
        lock_path: str | PathLike[str] | Path,
        timeout: float = 10.0,
    ) -> None:
        """Initialize AsyncFileLockAdapter.

        Args:
            lock_path: File path on disk for the lockfile.
            timeout: Default timeout in seconds for lock acquisition.
        """
        self._sync_adapter = FileLockAdapter(lock_path=lock_path, timeout=timeout)
        self._is_locked = False

    async def acquire(self, blocking: bool = True, timeout: float = -1.0) -> bool:
        """Acquire the file lock asynchronously in a worker thread.

        Args:
            blocking: Whether to wait for the lock.
            timeout: Maximum seconds to wait.

        Returns:
            True if acquired, False otherwise.
        """
        import asyncio

        acquired = await asyncio.to_thread(
            self._sync_adapter.acquire, blocking, timeout
        )
        if acquired:
            self._is_locked = True
        return acquired

    async def release(self) -> None:
        """Release the file lock asynchronously in a worker thread.

        Raises:
            LockError: If release fails.
        """
        import asyncio

        try:
            await asyncio.to_thread(self._sync_adapter.release)
        finally:
            self._is_locked = False

    async def locked(self) -> bool:
        """Check whether the file lock is currently held.

        Returns:
            True if held, False otherwise.
        """
        return self._is_locked


__all__ = [
    "AsyncFileLockAdapter",
    "FileLockAdapter",
]
