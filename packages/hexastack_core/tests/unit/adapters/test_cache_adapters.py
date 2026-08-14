import pytest

from hexastack_core.adapters.cache import AsyncInMemoryCache, InMemoryCache
from hexastack_core.adapters.clock import FrozenClock


def test_in_memory_cache_basic_crud():
    cache = InMemoryCache()
    assert cache.has("user:1") is False
    assert cache.get("user:1", "default") == "default"

    cache.set("user:1", {"name": "Alice"})
    assert cache.has("user:1") is True
    assert cache.get("user:1") == {"name": "Alice"}

    assert cache.delete("user:1") is True
    assert cache.has("user:1") is False

    cache.set("k1", "v1")
    cache.set("k2", "v2")
    cache.clear()
    assert cache.has("k1") is False


def test_in_memory_cache_ttl_expiration_with_frozen_clock():
    clock = FrozenClock()
    cache = InMemoryCache(clock=clock)

    cache.set("session:token", "active_data", ttl_seconds=60)
    assert cache.get("session:token") == "active_data"
    assert cache.has("session:token") is True

    # Advance clock by 30s (still valid)
    clock.advance(seconds=30)
    assert cache.get("session:token") == "active_data"

    # Advance clock by another 31s (61s total -> expired)
    clock.advance(seconds=31)
    assert cache.get("session:token") is None
    assert cache.has("session:token") is False


@pytest.mark.anyio
async def test_async_in_memory_cache():
    cache = AsyncInMemoryCache()
    assert await cache.has_async("item") is False

    await cache.set_async("item", 100)
    assert await cache.get_async("item") == 100
    assert await cache.has_async("item") is True

    assert await cache.delete_async("item") is True
    assert await cache.has_async("item") is False
