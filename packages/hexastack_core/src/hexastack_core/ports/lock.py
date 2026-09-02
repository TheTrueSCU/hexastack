from abc import ABC, abstractmethod
from types import TracebackType


class LockPort(ABC):
    """Abstract interface defining synchronous distributed mutual exclusion locks.

    Notes/Architectural Intent:
        Decouples services, outbox daemons, and transactional operations from specific
        distributed locking backends (e.g., in-memory threading locks, Redis/Valkey Redlock,
        etcd, ZooKeeper). Supports timeout-based acquisition and context manager usage.
    """

    @abstractmethod
    def acquire(self, blocking: bool = True, timeout: float = -1.0) -> bool:
        """Acquire the lock.

        Args:
            blocking: If True, blocks until the lock is acquired or timeout expires.
                If False, attempts immediate non-blocking acquisition.
            timeout: Maximum seconds to wait when blocking. Negative numbers indicate
                infinite blocking.

        Returns:
            True if the lock was successfully acquired, False otherwise.
        """

    @abstractmethod
    def release(self) -> None:
        """Release the acquired lock.

        Raises:
            LockError: If the lock was not acquired by the current caller or was lost.
        """

    @abstractmethod
    def locked(self) -> bool:
        """Check whether the lock is currently held.

        Returns:
            True if the lock is held, False otherwise.
        """

    def __enter__(self) -> bool:
        """Enter lock context, acquiring the lock in blocking mode.

        Returns:
            True if acquired.
        """
        return self.acquire(blocking=True)

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> None:
        """Exit lock context, releasing the lock."""
        _ = (exc_type, exc_val, exc_tb)
        self.release()


class AsyncLockPort(ABC):
    """Abstract interface defining asynchronous distributed mutual exclusion locks.

    Notes/Architectural Intent:
        Async counterpart to LockPort for asyncio-native service pipelines, coroutine
        orchestrators, and asynchronous queue consumers.
    """

    @abstractmethod
    async def acquire(self, blocking: bool = True, timeout: float = -1.0) -> bool:
        """Acquire the lock asynchronously.

        Args:
            blocking: If True, awaits acquisition until acquired or timeout expires.
                If False, attempts immediate non-blocking acquisition.
            timeout: Maximum seconds to wait when blocking. Negative numbers indicate
                infinite blocking.

        Returns:
            True if the lock was successfully acquired, False otherwise.
        """

    @abstractmethod
    async def release(self) -> None:
        """Release the acquired lock asynchronously.

        Raises:
            LockError: If the lock was not acquired by the current caller or was lost.
        """

    @abstractmethod
    async def locked(self) -> bool:
        """Check whether the lock is currently held asynchronously.

        Returns:
            True if the lock is held, False otherwise.
        """

    async def __aenter__(self) -> bool:
        """Enter async lock context, acquiring the lock in blocking mode.

        Returns:
            True if acquired.
        """
        return await self.acquire(blocking=True)

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> None:
        """Exit async lock context, releasing the lock."""
        _ = (exc_type, exc_val, exc_tb)
        await self.release()


__all__ = [
    "AsyncLockPort",
    "LockPort",
]
