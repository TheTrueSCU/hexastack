"""Hypothesis RuleBasedStateMachine dual-implementation oracle tests for InMemoryRateLimiter.

Notes/Architectural Intent:
    Validates that InMemoryRateLimiter (production rate limiter port adapter) and
    NaiveSlidingWindowOracle yield identical admission decisions, remaining reset
    windows, and key eviction states across arbitrary time advancement sequences,
    burst workloads, and key allocations under Hypothesis fuzz generation.
"""

from collections import defaultdict
from datetime import UTC, datetime

from hypothesis import strategies as st
from hypothesis.stateful import (
    RuleBasedStateMachine,
    invariant,
    rule,
)

from hexastack_core.adapters.clock.in_memory import FrozenClock
from hexastack_core.adapters.ratelimit import InMemoryRateLimiter, _parse_rate_limit


class NaiveSlidingWindowOracle:
    """Brute-force reference sliding-window rate limit oracle.

    Notes/Architectural Intent:
        Keeps a raw list of timestamps per key and applies simple list comprehensions
        to verify that production rate limiting logic has zero divergence or edge-case off-by-one errors.
    """

    def __init__(self) -> None:
        """Initialize empty reference oracle."""
        self.hits: dict[str, list[float]] = defaultdict(list)

    def hit(self, key: str, count: int, window_seconds: int, timestamp: float) -> bool:
        """Evaluate and record hit against rate limit window.

        Args:
            key: Rate limiting bucket key.
            count: Maximum hits allowed in window.
            window_seconds: Window duration in seconds.
            timestamp: Current timestamp in seconds.

        Returns:
            True if hit is within quota, False if exceeded.
        """
        window_start = timestamp - window_seconds
        valid_hits = [t for t in self.hits[key] if t > window_start]
        self.hits[key] = valid_hits

        if len(valid_hits) < count:
            self.hits[key].append(timestamp)
            return True
        return False

    def get_reset_window(
        self, key: str, count: int, window_seconds: int, timestamp: float
    ) -> int:
        """Calculate remaining seconds until window reset.

        Args:
            key: Rate limiting bucket key.
            count: Maximum hits allowed in window.
            window_seconds: Window duration in seconds.
            timestamp: Current timestamp in seconds.

        Returns:
            Remaining seconds until reset.
        """
        window_start = timestamp - window_seconds
        valid_hits = [t for t in self.hits[key] if t > window_start]
        if not valid_hits or len(valid_hits) < count:
            return 0
        oldest_hit = valid_hits[0]
        remaining = int((oldest_hit + window_seconds) - timestamp)
        return max(1, remaining)

    def clear(self, key: str | None = None) -> None:
        """Clear rate limit counters for a key or all keys.

        Args:
            key: Optional specific key to reset.
        """
        if key is not None:
            self.hits.pop(key, None)
        else:
            self.hits.clear()


KEY_STRATEGY = st.sampled_from(
    [
        "user:101",
        "user:102",
        "user:103",
        "ip:192.168.1.1",
        "anon:guest",
    ]
)
LIMIT_STRATEGY = st.sampled_from(
    [
        "3/second",
        "5/s",
        "10/minute",
        "2/min",
        "100/hour",
    ]
)
DELTA_SECONDS_STRATEGY = st.floats(min_value=0.0, max_value=120.0)


class RateLimiterOracleStateMachine(RuleBasedStateMachine):
    """Hypothesis state machine validating InMemoryRateLimiter against NaiveSlidingWindowOracle.

    Notes/Architectural Intent:
        Exercises erratic non-decreasing time jumps, bursts of hits, reset window queries,
        and cache clears across multiple independent rate limit keys.
    """

    def __init__(self) -> None:
        """Initialize state machine with frozen clock and dual limiters."""
        super().__init__()
        self.clock = FrozenClock(datetime(2026, 1, 1, 12, 0, 0, tzinfo=UTC))
        self.limiter = InMemoryRateLimiter(clock=self.clock)
        self.oracle = NaiveSlidingWindowOracle()

    @rule(seconds=DELTA_SECONDS_STRATEGY)
    def advance_time(self, seconds: float) -> None:
        """Advance simulated clock by a random non-negative duration.

        Args:
            seconds: Duration in seconds to advance.
        """
        self.clock.advance(seconds=seconds)

    @rule(key=KEY_STRATEGY, limit_str=LIMIT_STRATEGY)
    def record_hit(self, key: str, limit_str: str) -> None:
        """Record a hit against rate limiter and verify oracle parity.

        Args:
            key: Target rate limiting key.
            limit_str: Limit specification string.
        """
        spec = _parse_rate_limit(limit_str)
        current_time = self.clock.timestamp()

        actual_allowed = self.limiter.hit(key, limit_str)
        oracle_allowed = self.oracle.hit(
            key=key,
            count=spec.count,
            window_seconds=spec.window_seconds,
            timestamp=current_time,
        )
        assert actual_allowed is oracle_allowed

        actual_reset = self.limiter.get_reset_window(key, limit_str)
        oracle_reset = self.oracle.get_reset_window(
            key=key,
            count=spec.count,
            window_seconds=spec.window_seconds,
            timestamp=current_time,
        )
        assert actual_reset == oracle_reset

    @rule(key=KEY_STRATEGY, limit_str=LIMIT_STRATEGY)
    def check_reset_window(self, key: str, limit_str: str) -> None:
        """Verify remaining reset window calculation matches oracle without recording a hit.

        Args:
            key: Target rate limiting key.
            limit_str: Limit specification string.
        """
        spec = _parse_rate_limit(limit_str)
        current_time = self.clock.timestamp()

        actual_reset = self.limiter.get_reset_window(key, limit_str)
        oracle_reset = self.oracle.get_reset_window(
            key=key,
            count=spec.count,
            window_seconds=spec.window_seconds,
            timestamp=current_time,
        )
        assert actual_reset == oracle_reset

    @rule(key=KEY_STRATEGY)
    def clear_key(self, key: str) -> None:
        """Clear rate limit history for a specific key.

        Args:
            key: Target key to clear.
        """
        self.limiter.clear(key)
        self.oracle.clear(key)
        assert key not in self.limiter._hits
        assert key not in self.oracle.hits

    @rule()
    def clear_all(self) -> None:
        """Clear all rate limit history."""
        self.limiter.clear()
        self.oracle.clear()
        hits_len = len(self.limiter._hits)
        assert hits_len == 0
        oracle_len = len(self.oracle.hits)
        assert oracle_len == 0

    @invariant()
    def timestamp_history_parity(self) -> None:
        """Invariant: verified timestamp lists match exactly across all tracked keys."""
        all_keys = set(self.limiter._hits.keys()) | set(self.oracle.hits.keys())
        for k in all_keys:
            limiter_ts = self.limiter._hits.get(k, [])
            oracle_ts = self.oracle.hits.get(k, [])
            assert limiter_ts == oracle_ts


TestRateLimiterOracle = RateLimiterOracleStateMachine.TestCase
