"""Performance microbenchmarks for in-memory caching and rate limiting adapters.

Notes/Architectural Intent:
    Measures sub-microsecond dictionary access and sliding window timestamp eviction
    overheads in InMemoryCache and InMemoryRateLimiter foundation adapters.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from hexastack_core.adapters.cache.in_memory import InMemoryCache
from hexastack_core.adapters.ratelimit import InMemoryRateLimiter

if TYPE_CHECKING:
    from pytest_benchmark.fixture import BenchmarkFixture


def test_perf_cache_get_hit(benchmark: BenchmarkFixture) -> None:
    """Benchmark InMemoryCache.get latency on existing cache hit.

    Args:
        benchmark: pytest-benchmark fixture.

    Notes/Architectural Intent:
        Quantifies baseline dictionary lookup and TTL expiration verification latency.
    """
    cache = InMemoryCache()
    cache.set("bench:key", "bench_payload", ttl_seconds=3600)

    val = benchmark(cache.get, "bench:key")
    assert val == "bench_payload"


def test_perf_cache_set(benchmark: BenchmarkFixture) -> None:
    """Benchmark InMemoryCache.set insertion latency.

    Args:
        benchmark: pytest-benchmark fixture.

    Notes/Architectural Intent:
        Quantifies tuple creation and dictionary assignment overhead.
    """
    cache = InMemoryCache()

    benchmark(cache.set, "bench:insert", 12345, ttl_seconds=60)
    res = cache.get("bench:insert")
    assert res == 12345


def test_perf_ratelimit_sliding_window(benchmark: BenchmarkFixture) -> None:
    """Benchmark InMemoryRateLimiter sliding window hit evaluation latency.

    Args:
        benchmark: pytest-benchmark fixture.

    Notes/Architectural Intent:
        Quantifies lock acquisition, timestamp recording, and list comprehension
        eviction overhead under rapid successive requests without unbounded list growth.
    """
    limiter = InMemoryRateLimiter()

    def _hit_bounded() -> bool:
        allowed = limiter.hit("bench:client", "1000/minute")
        hits = limiter._hits.get("bench:client")
        if hits and len(hits) > 50:
            del hits[:25]
        return allowed

    res = benchmark(_hit_bounded)
    assert res is True
