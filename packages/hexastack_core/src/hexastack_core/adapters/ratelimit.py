import time
from typing import NamedTuple

from hexastack_core.ports.ratelimit import RateLimiterPort


class _RateLimitSpec(NamedTuple):
    count: int
    window_seconds: int


def _parse_rate_limit(limit_str: str) -> _RateLimitSpec:
    """Parse rate limit string like '10/minute', '5/second', '100/hour', '1000/day'.

    Args:
        limit_str: Rate string in format '<count>/<unit>'.

    Returns:
        _RateLimitSpec with count and window duration in seconds.

    Raises:
        ValueError: If limit_str format is invalid.
    """
    parts = limit_str.strip().split("/")
    if len(parts) != 2:
        raise ValueError(
            f"Invalid rate limit format '{limit_str}'. Expected format '<count>/<unit>' (e.g. '10/minute')."
        )
    count_str, unit_str = parts[0].strip(), parts[1].strip().lower()
    try:
        count = int(count_str)
    except ValueError as e:
        raise ValueError(
            f"Invalid rate limit count '{count_str}' in '{limit_str}'."
        ) from e

    multipliers = {
        "second": 1,
        "sec": 1,
        "s": 1,
        "minute": 60,
        "min": 60,
        "m": 60,
        "hour": 3600,
        "hr": 3600,
        "h": 3600,
        "day": 86400,
        "d": 86400,
    }
    unit = unit_str.rstrip("s")
    if unit not in multipliers:
        raise ValueError(
            f"Invalid rate limit time unit '{unit_str}' in '{limit_str}'. Supported units: second, minute, hour, day."
        )
    return _RateLimitSpec(count=count, window_seconds=multipliers[unit])


class InMemoryRateLimiter(RateLimiterPort):
    """In-memory sliding window rate limiter implementation.

    Notes/Architectural Intent:
        Provides lightweight, zero-dependency rate limiting for unit tests, local development,
        and single-node deployments using sliding timestamp logs.
    """

    def __init__(self) -> None:
        """Initialize empty in-memory rate limiter."""
        # Key -> list of hit timestamps
        self._hits: dict[str, list[float]] = {}

    def hit(self, key: str, limit: str) -> bool:
        """Record a hit against a rate limit window and return whether it is allowed.

        Args:
            key: Rate limiting bucket key.
            limit: Limit rate string (e.g. '10/minute').

        Returns:
            True if hit is within quota, False if exceeded.
        """
        spec = _parse_rate_limit(limit)
        now = time.time()
        window_start = now - spec.window_seconds

        timestamps = self._hits.setdefault(key, [])
        # Evict timestamps outside sliding window
        self._hits[key] = [t for t in timestamps if t > window_start]

        if len(self._hits[key]) < spec.count:
            self._hits[key].append(now)
            return True
        return False

    def get_reset_window(self, key: str, limit: str) -> int:
        """Get the remaining seconds until the current rate limit window resets.

        Args:
            key: Rate limiting bucket key.
            limit: Limit rate string.

        Returns:
            Remaining seconds until reset (minimum 1 second).
        """
        spec = _parse_rate_limit(limit)
        now = time.time()
        window_start = now - spec.window_seconds

        timestamps = self._hits.get(key, [])
        valid_timestamps = [t for t in timestamps if t > window_start]
        if not valid_timestamps or len(valid_timestamps) < spec.count:
            return 0

        oldest_hit = valid_timestamps[0]
        remaining = int((oldest_hit + spec.window_seconds) - now)
        return max(1, remaining)

    def clear(self, key: str | None = None) -> None:
        """Clear rate limit counters for a specific key or all keys.

        Args:
            key: Optional specific key to reset.
        """
        if key is not None:
            self._hits.pop(key, None)
        else:
            self._hits.clear()


__all__ = [
    "InMemoryRateLimiter",
]
