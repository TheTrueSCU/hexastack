import asyncio

from hexastack_core.adapters.cache import AsyncInMemoryCache, InMemoryCache
from hexastack_core.adapters.clock import FrozenClock


def test_async_in_memory_cache():
    async def _run():
        clock = FrozenClock()
        cache = AsyncInMemoryCache(clock=clock)
        assert await cache.has_async("item") is False

        await cache.set_async("item", 100, ttl_seconds=10)
        assert await cache.get_async("item") == 100
        assert await cache.has_async("item") is True

        clock.advance(seconds=11)
        assert await cache.has_async("item") is False
        assert await cache.get_async("item") is None

        await cache.set_async("item", 200)
        del_res = await cache.delete_async("item")
        assert del_res is True
        has_after_del = await cache.has_async("item")
        assert has_after_del is False

        await cache.set_async("item1", 1)
        await cache.set_async("item2", 2)
        await cache.clear_async()
        assert await cache.has_async("item1") is False

    asyncio.run(_run())


def test_in_memory_cache_basic_crud():
    cache = InMemoryCache()
    assert cache.has("user:1") is False
    assert cache.get("user:1", "default") == "default"

    cache.set("user:1", {"name": "Alice"})
    assert cache.has("user:1") is True
    assert cache.get("user:1") == {"name": "Alice"}

    deleted = cache.delete("user:1")
    assert deleted is True
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

    # Advance clock by 30s (still valid: now < expiry)
    clock.advance(seconds=30)
    assert cache.get("session:token") == "active_data"
    assert cache.has("session:token") is True

    # Advance clock by exact remaining time (now == expiry: 60s total, not > expiry yet)
    clock.advance(seconds=30)
    assert cache.get("session:token") == "active_data"
    assert cache.has("session:token") is True

    # Advance clock by 0.001s (now > expiry -> expired and deleted)
    clock.advance(seconds=0.001)
    assert cache.get("session:token") is None
    assert cache.has("session:token") is False
    assert "session:token" not in cache._store
