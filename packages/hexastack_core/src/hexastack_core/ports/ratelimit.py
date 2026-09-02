from abc import ABC, abstractmethod


class RateLimiterPort(ABC):
    """Abstract interface defining rate limiting and quota verification operations.

    Notes/Architectural Intent:
        Decouples HTTP presentation layers, gRPC interceptors, and application services
        from specific rate limiting implementations (e.g. In-Memory token bucket,
        slowapi/limits, Redis sliding window).
    """

    @abstractmethod
    def hit(self, key: str, limit: str) -> bool:
        """Record a hit against a rate limit window and return whether it is allowed.

        Args:
            key: Rate limiting bucket key (e.g. IP, tenant_id, user_id).
            limit: Limit rate string (e.g. '10/minute', '100/hour', '5/second').

        Returns:
            True if the hit is within quota, False if rate limit is exceeded.
        """

    @abstractmethod
    def get_reset_window(self, key: str, limit: str) -> int:
        """Get the remaining seconds until the current rate limit window resets.

        Args:
            key: Rate limiting bucket key.
            limit: Limit rate string.

        Returns:
            Remaining seconds until reset (used for Retry-After headers).
        """

    @abstractmethod
    def clear(self, key: str | None = None) -> None:
        """Clear rate limit counters for a specific key or all keys.

        Args:
            key: Optional specific key to reset. If None, resets all rate limit tracking.
        """


__all__ = [
    "RateLimiterPort",
]
