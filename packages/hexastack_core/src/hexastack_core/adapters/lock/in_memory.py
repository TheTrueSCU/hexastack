import asyncio
import threading
from typing import Any

from hexastack_core.domain.exceptions import LockError
from hexastack_core.ports.lock import AsyncLockPort, LockPort


class InMemoryLock(LockPort):
    """Thread-safe reentrant in-memory mutual exclusion lock adapter.

    Notes/Architectural Intent:
        Implements LockPort using Python's standard library threading.RLock with
        recursion tracking. Prevents threads from blocking themselves in nested scopes.
    """

    def __init__(self) -> None:
        """Initialize InMemoryLock."""
        self._lock = threading.RLock()
        self._count = 0
        self._owner_thread: int | None = None

    def acquire(self, blocking: bool = True, timeout: float = -1.0) -> bool:
        """Acquire the in-memory lock (reentrant).

        Args:
            blocking: Whether to block waiting for the lock.
            timeout: Timeout in seconds if blocking.

        Returns:
            True if acquired, False otherwise.
        """
        acquired = self._lock.acquire(blocking=blocking, timeout=timeout)
        if acquired:
            self._count += 1
            self._owner_thread = threading.get_ident()
        return acquired

    def release(self) -> None:
        """Release the in-memory lock.

        Raises:
            LockError: If the lock was not held by the current thread.
        """
        if self._count <= 0 or self._owner_thread != threading.get_ident():
            raise LockError(
                "Cannot release an unacquired lock or a lock owned by another thread."
            )
        try:
            self._lock.release()
            self._count -= 1
            if self._count == 0:
                self._owner_thread = None
        except RuntimeError as e:
            raise LockError(str(e)) from e

    def locked(self) -> bool:
        """Check if the lock is held.

        Returns:
            True if held, False otherwise.
        """
        return self._count > 0


class AsyncInMemoryLock(AsyncLockPort):
    """Coroutine-safe reentrant in-memory asynchronous mutual exclusion lock adapter.

    Notes/Architectural Intent:
        Implements AsyncLockPort with Task-aware reentrancy (analogous to threading.RLock).
        Prevents asyncio tasks from deadlocking themselves when calling nested locked workflows.
    """

    def __init__(self) -> None:
        """Initialize AsyncInMemoryLock."""
        self._lock = asyncio.Lock()
        self._owner: asyncio.Task[Any] | None = None
        self._count = 0

    async def acquire(self, blocking: bool = True, timeout: float = -1.0) -> bool:
        """Acquire the async lock (reentrant per asyncio.Task).

        Args:
            blocking: Whether to wait for lock availability.
            timeout: Timeout in seconds if blocking.

        Returns:
            True if acquired, False otherwise.
        """
        current_task = asyncio.current_task()
        if self._owner is not None and self._owner == current_task:
            self._count += 1
            return True

        if not blocking:
            if self._lock.locked():
                return False
            await self._lock.acquire()
            self._owner = current_task
            self._count = 1
            return True

        if timeout < 0:
            await self._lock.acquire()
            self._owner = current_task
            self._count = 1
            return True

        try:
            await asyncio.wait_for(self._lock.acquire(), timeout=timeout)
            self._owner = current_task
            self._count = 1
            return True
        except TimeoutError:
            return False

    async def release(self) -> None:
        """Release the async lock.

        Raises:
            LockError: If the lock is not currently acquired by the current task.
        """
        current_task = asyncio.current_task()
        if self._owner != current_task or self._count <= 0:
            raise LockError(
                "Cannot release an unacquired lock or a lock owned by another task."
            )

        self._count -= 1
        if self._count == 0:
            self._owner = None
            self._lock.release()

    async def locked(self) -> bool:
        """Check if the lock is currently held.

        Returns:
            True if held, False otherwise.
        """
        return self._count > 0


__all__ = [
    "AsyncInMemoryLock",
    "InMemoryLock",
]
