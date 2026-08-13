from abc import ABC, abstractmethod
from datetime import datetime


class ClockPort(ABC):
    """Abstract interface for system time operations.

    Notes/Architectural Intent:
        Enables deterministic testing of time-dependent workflows (cache TTL,
        retry backoff, timestamp creation, token expiration) without relying
        on system clock or sleep calls.
    """

    @abstractmethod
    def now_utc(self) -> datetime:
        """Return the current UTC datetime.

        Returns:
            Current datetime in UTC timezone.
        """
        ...

    @abstractmethod
    def timestamp(self) -> float:
        """Return the current Unix timestamp in seconds.

        Returns:
            Current POSIX timestamp as float.
        """
        ...


__all__ = [
    "ClockPort",
]
