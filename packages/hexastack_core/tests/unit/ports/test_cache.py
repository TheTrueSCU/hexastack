import inspect

import pytest

from hexastack_core.adapters.cache import AsyncInMemoryCache, InMemoryCache
from hexastack_core.ports.cache import AsyncCachePort, CachePort


def test_cache_port_is_abstract() -> None:
    """Verify CachePort cannot be directly instantiated and defines abstract contract."""
    is_abs = inspect.isabstract(CachePort)
    assert is_abs is True
    with pytest.raises(TypeError, match="Can't instantiate abstract class"):
        CachePort()  # ty: ignore[call-non-callable] # type: ignore[abstract]

    expected = {"clear", "delete", "get", "has", "set"}
    diff = expected.difference(CachePort.__abstractmethods__)
    assert len(diff) == 0


def test_async_cache_port_is_abstract() -> None:
    """Verify AsyncCachePort cannot be directly instantiated and defines abstract contract."""
    is_abs = inspect.isabstract(AsyncCachePort)
    assert is_abs is True
    with pytest.raises(TypeError, match="Can't instantiate abstract class"):
        AsyncCachePort()  # ty: ignore[call-non-callable] # type: ignore[abstract]

    expected = {"clear_async", "delete_async", "get_async", "has_async", "set_async"}
    diff = expected.difference(AsyncCachePort.__abstractmethods__)
    assert len(diff) == 0


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
