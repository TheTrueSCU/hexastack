import asyncio
import threading

from hexastack_core.domain.exceptions import LockError
from hexastack_core.ports.lock import AsyncLockPort, LockPort


class InMemoryLock(LockPort):
    """Thread-safe in-memory mutual exclusion lock adapter.

    Notes/Architectural Intent:
        Implements LockPort using Python's standard library threading.RLock.
        Suitable for single-process test fixtures, local development, and monolithic setups.
    """

    def __init__(self) -> None:
        """Initialize InMemoryLock."""
        self._lock = threading.RLock()
        self._is_locked = False
        self._owner_thread: int | None = None

    def acquire(self, blocking: bool = True, timeout: float = -1.0) -> bool:
        """Acquire the in-memory lock.

        Args:
            blocking: Whether to block waiting for the lock.
            timeout: Timeout in seconds if blocking.

        Returns:
            True if acquired, False otherwise.
        """
        acquired = self._lock.acquire(blocking=blocking, timeout=timeout)
        if acquired:
            self._is_locked = True
            self._owner_thread = threading.get_ident()
        return acquired

    def release(self) -> None:
        """Release the in-memory lock.

        Raises:
            LockError: If the lock was not held by the current thread.
        """
        if not self._is_locked or self._owner_thread != threading.get_ident():
            raise LockError(
                "Cannot release an unacquired lock or a lock owned by another thread."
            )
        try:
            self._lock.release()
        except RuntimeError as e:
            raise LockError(str(e)) from e
        finally:
            self._is_locked = False
            self._owner_thread = None

    def locked(self) -> bool:
        """Check if the lock is held.

        Returns:
            True if held, False otherwise.
        """
        return self._is_locked


class AsyncInMemoryLock(AsyncLockPort):
    """Coroutine-safe in-memory asynchronous mutual exclusion lock adapter.

    Notes/Architectural Intent:
        Implements AsyncLockPort using asyncio.Lock and asyncio.wait_for.
        Suitable for unit testing async workflows, outbox consumers, and in-memory event channels.
    """

    def __init__(self) -> None:
        """Initialize AsyncInMemoryLock."""
        self._lock = asyncio.Lock()

    async def acquire(self, blocking: bool = True, timeout: float = -1.0) -> bool:
        """Acquire the async lock.

        Args:
            blocking: Whether to wait for lock availability.
            timeout: Timeout in seconds if blocking.

        Returns:
            True if acquired, False otherwise.
        """
        if not blocking:
            if self._lock.locked():
                return False
            await self._lock.acquire()
            return True

        if timeout < 0:
            await self._lock.acquire()
            return True

        try:
            await asyncio.wait_for(self._lock.acquire(), timeout=timeout)
            return True
        except TimeoutError:
            return False

    async def release(self) -> None:
        """Release the async lock.

        Raises:
            LockError: If the lock is not currently acquired.
        """
        if not self._lock.locked():
            raise LockError("Cannot release an unacquired lock.")
        try:
            self._lock.release()
        except RuntimeError as e:
            raise LockError(str(e)) from e

    async def locked(self) -> bool:
        """Check if the lock is currently held.

        Returns:
            True if held, False otherwise.
        """
        return self._lock.locked()


__all__ = [
    "AsyncInMemoryLock",
    "InMemoryLock",
]
