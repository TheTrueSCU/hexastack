import pytest

from hexastack_core.adapters.cache import AsyncInMemoryCache, InMemoryCache
from hexastack_core.ports.cache import AsyncCachePort, CachePort


@pytest.mark.anyio
async def test_async_cache_port_contract():
    cache: AsyncCachePort = AsyncInMemoryCache()
    assert await cache.has_async("k") is False
    await cache.set_async("k", "v")
    assert await cache.has_async("k") is True
    assert await cache.get_async("k") == "v"
    deleted_async = await cache.delete_async("k")
    assert deleted_async is True
    assert await cache.has_async("k") is False


def test_sync_cache_port_contract():
    cache: CachePort = InMemoryCache()
    assert cache.has("k") is False
    cache.set("k", "v")
    assert cache.has("k") is True
    assert cache.get("k") == "v"
    deleted = cache.delete("k")
    assert deleted is True
    assert cache.has("k") is False
