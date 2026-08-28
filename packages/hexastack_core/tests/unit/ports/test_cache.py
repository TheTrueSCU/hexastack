from typing import Any

import pytest

from hexastack_core.ports.cache import AsyncCachePort, CachePort


class MockCache(CachePort):
    def __init__(self) -> None:
        self.data: dict[str, Any] = {}

    def clear(self) -> None:
        self.data.clear()

    def delete(self, key: str) -> bool:
        return self.data.pop(key, None) is not None

    def get(self, key: str, default: Any = None) -> Any:
        return self.data.get(key, default)

    def has(self, key: str) -> bool:
        return key in self.data

    def set(self, key: str, value: Any, ttl_seconds: float | None = None) -> None:
        self.data[key] = value


class MockAsyncCache(AsyncCachePort):
    def __init__(self) -> None:
        self._sync = MockCache()

    async def clear_async(self) -> None:
        self._sync.clear()

    async def delete_async(self, key: str) -> bool:
        return self._sync.delete(key)

    async def get_async(self, key: str, default: Any = None) -> Any:
        return self._sync.get(key, default)

    async def has_async(self, key: str) -> bool:
        return self._sync.has(key)

    async def set_async(
        self, key: str, value: Any, ttl_seconds: float | None = None
    ) -> None:
        self._sync.set(key, value, ttl_seconds)


@pytest.mark.anyio
async def test_async_cache_port_contract():
    cache: AsyncCachePort = MockAsyncCache()
    assert await cache.has_async("k") is False
    await cache.set_async("k", "v")
    assert await cache.has_async("k") is True
    assert await cache.get_async("k") == "v"
    deleted_async = await cache.delete_async("k")
    assert deleted_async is True
    assert await cache.has_async("k") is False


def test_cache_port_contract():
    cache: CachePort = MockCache()
    assert cache.has("k") is False
    cache.set("k", 123)
    assert cache.has("k") is True
    assert cache.get("k") == 123
    deleted = cache.delete("k")
    assert deleted is True
    assert cache.has("k") is False
