"""Hypothesis RuleBasedStateMachine dual-implementation oracle tests for Cache adapters.

Notes/Architectural Intent:
    Validates that DiskCacheAdapter (persistent SQLite L2 cache), InMemoryCacheAdapter
    (in-memory L1 cache), and NaiveDictCacheOracle maintain identical key-value retrieval,
    existence checks, deletion idempotency, and TTL expiration behavior across arbitrary
    interleaved operations and time progressions under Hypothesis fuzz generation.
"""

import tempfile
from datetime import UTC, datetime
from typing import Any

from hypothesis import strategies as st
from hypothesis.stateful import (
    RuleBasedStateMachine,
    invariant,
    rule,
)

from hexastack_core.adapters.cache.disk import DiskCacheAdapter
from hexastack_core.adapters.cache.in_memory import InMemoryCache
from hexastack_core.adapters.clock.in_memory import FrozenClock


class NaiveDictCacheOracle:
    """Pure Python reference oracle for key-value caching with TTL semantics.

    Notes/Architectural Intent:
        Implements mathematically simple dictionary-based caching with TTL expiration
        to serve as the differential ground-truth oracle for DiskCacheAdapter and InMemoryCache.
    """

    def __init__(self) -> None:
        """Initialize empty reference cache oracle."""
        self._store: dict[str, tuple[Any, float | None]] = {}

    def get(self, key: str, timestamp: float, default: Any = None) -> Any:
        """Retrieve value if unexpired, or return default.

        Args:
            key: Cache key identifier.
            timestamp: Current timestamp in seconds.
            default: Default fallback value.

        Returns:
            Cached value if unexpired, else default.
        """
        if key not in self._store:
            return default
        val, expiry = self._store[key]
        if expiry is not None and timestamp > expiry:
            del self._store[key]
            return default
        return val

    def has(self, key: str, timestamp: float) -> bool:
        """Check if key exists and is unexpired.

        Args:
            key: Cache key identifier.
            timestamp: Current timestamp in seconds.

        Returns:
            True if present and unexpired, else False.
        """
        return self.get(key, timestamp=timestamp, default=None) is not None

    def set(
        self,
        key: str,
        value: Any,
        timestamp: float,
        ttl_seconds: float | None = None,
    ) -> None:
        """Store key-value pair with optional expiration timestamp.

        Args:
            key: Cache key identifier.
            value: Value payload.
            timestamp: Current timestamp in seconds.
            ttl_seconds: Optional time-to-live duration.
        """
        expiry = (timestamp + ttl_seconds) if ttl_seconds is not None else None
        self._store[key] = (value, expiry)

    def delete(self, key: str) -> bool:
        """Remove key from store, returning True if key existed.

        Args:
            key: Cache key identifier.

        Returns:
            True if key existed, False otherwise.
        """
        return self._store.pop(key, None) is not None

    def clear(self) -> None:
        """Purge all entries from the store."""
        self._store.clear()


TRACKED_KEYS = [
    "user:1",
    "user:2",
    "session:token",
    "item:meta",
    "temp:rate",
]
KEY_STRATEGY = st.sampled_from(TRACKED_KEYS)
VALUE_STRATEGY = st.one_of(
    st.integers(-1000, 1000),
    st.text(min_size=1, max_size=20, alphabet=st.characters(categories=["L"])),
    st.booleans(),
    st.dictionaries(
        st.text(min_size=1, max_size=5, alphabet=st.characters(categories=["L"])),
        st.integers(0, 10),
        max_size=2,
    ),
)
TTL_STRATEGY = st.one_of(st.none(), st.floats(min_value=1.0, max_value=60.0))
DELTA_STRATEGY = st.floats(min_value=0.0, max_value=70.0)


class CacheOracleStateMachine(RuleBasedStateMachine):
    """Hypothesis state machine verifying triple cache implementation equivalence.

    Notes/Architectural Intent:
        Exercises arbitrary interleaved sets, gets, deletes, clears, and clock advancements,
        proving that DiskCacheAdapter, InMemoryCacheAdapter, and NaiveDictCacheOracle
        remain completely synchronized at all times.
    """

    def __init__(self) -> None:
        """Initialize state machine with isolated tempdir and dual cache adapters."""
        super().__init__()
        self.tmpdir = tempfile.TemporaryDirectory()
        self.clock = FrozenClock(datetime(2026, 1, 1, 12, 0, 0, tzinfo=UTC))
        self.disk_cache = DiskCacheAdapter(directory=self.tmpdir.name, clock=self.clock)
        self.mem_cache = InMemoryCache(clock=self.clock)
        self.oracle = NaiveDictCacheOracle()

    def teardown(self) -> None:
        """Cleanly close disk cache database handles and remove tempdir."""
        self.disk_cache.close()
        self.tmpdir.cleanup()

    @rule(seconds=DELTA_STRATEGY)
    def advance_time(self, seconds: float) -> None:
        """Advance simulated clock by a random duration.

        Args:
            seconds: Seconds to advance.
        """
        self.clock.advance(seconds=seconds)

    @rule(key=KEY_STRATEGY, value=VALUE_STRATEGY, ttl=TTL_STRATEGY)
    def set_key(self, key: str, value: Any, ttl: float | None) -> None:
        """Store key-value pair across all cache implementations and assert retrieval.

        Args:
            key: Target cache key.
            value: Value payload.
            ttl: Optional TTL expiration in seconds.
        """
        now = self.clock.timestamp()
        self.disk_cache.set(key, value, ttl_seconds=ttl)
        self.mem_cache.set(key, value, ttl_seconds=ttl)
        self.oracle.set(key, value, timestamp=now, ttl_seconds=ttl)

        d_val = self.disk_cache.get(key)
        m_val = self.mem_cache.get(key)
        o_val = self.oracle.get(key, timestamp=now)
        assert d_val == o_val
        assert m_val == o_val

    @rule(key=KEY_STRATEGY)
    def get_key(self, key: str) -> None:
        """Retrieve key across all caches and verify value and existence parity.

        Args:
            key: Target cache key.
        """
        now = self.clock.timestamp()
        d_val = self.disk_cache.get(key)
        m_val = self.mem_cache.get(key)
        o_val = self.oracle.get(key, timestamp=now)
        assert d_val == o_val
        assert m_val == o_val

        d_has = self.disk_cache.has(key)
        m_has = self.mem_cache.has(key)
        o_has = self.oracle.has(key, timestamp=now)
        assert d_has is o_has
        assert m_has is o_has

    @rule(key=KEY_STRATEGY)
    def delete_key(self, key: str) -> None:
        """Delete key across all caches and verify deletion boolean parity.

        Args:
            key: Target cache key.
        """
        d_del = self.disk_cache.delete(key)
        m_del = self.mem_cache.delete(key)
        o_del = self.oracle.delete(key)
        assert d_del is o_del
        assert m_del is o_del

    @rule()
    def clear_caches(self) -> None:
        """Clear all entries across all caches."""
        self.disk_cache.clear()
        self.mem_cache.clear()
        self.oracle.clear()

    @invariant()
    def caches_state_equivalence(self) -> None:
        """Invariant: all tracked keys return identical values and existence across all caches."""
        now = self.clock.timestamp()
        for key in TRACKED_KEYS:
            d_val = self.disk_cache.get(key)
            m_val = self.mem_cache.get(key)
            o_val = self.oracle.get(key, timestamp=now)
            assert d_val == o_val
            assert m_val == o_val

            d_has = self.disk_cache.has(key)
            m_has = self.mem_cache.has(key)
            o_has = self.oracle.has(key, timestamp=now)
            assert d_has is o_has
            assert m_has is o_has


TestCacheOracle = CacheOracleStateMachine.TestCase
