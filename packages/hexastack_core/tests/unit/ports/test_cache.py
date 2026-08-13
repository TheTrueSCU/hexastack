from typing import Any

import pytest
from hexastack_core.ports.cache import AsyncCachePort, CachePort


class MockCache(CachePort):
    def __init__(self) -> None:
        self.data: dict[str, Any] = {}

    def get(self, key: str, default: Any = None) -> Any:
        return self.data.get(key, default)

    def set(self, key: str, value: Any, ttl_seconds: float | None = None) -> None:
        self.data[key] = value

    def delete(self, key: str) -> bool:
        return self.data.pop(key, None) is not None

    def has(self, key: str) -> bool:
        return key in self.data

    def clear(self) -> None:
        self.data.clear()


class MockAsyncCache(AsyncCachePort):
    def __init__(self) -> None:
        self._sync = MockCache()

    async def get_async(self, key: str, default: Any = None) -> Any:
        return self._sync.get(key, default)

    async def set_async(
        self, key: str, value: Any, ttl_seconds: float | None = None
    ) -> None:
        self._sync.set(key, value, ttl_seconds)

    async def delete_async(self, key: str) -> bool:
        return self._sync.delete(key)

    async def has_async(self, key: str) -> bool:
        return self._sync.has(key)

    async def clear_async(self) -> None:
        self._sync.clear()


def test_cache_port_contract():
    cache: CachePort = MockCache()
    assert cache.has("k") is False
    cache.set("k", 123)
    assert cache.has("k") is True
    assert cache.get("k") == 123
    assert cache.delete("k") is True
    assert cache.has("k") is False


@pytest.mark.anyio
async def test_async_cache_port_contract():
    cache: AsyncCachePort = MockAsyncCache()
    assert await cache.has_async("k") is False
    await cache.set_async("k", "v")
    assert await cache.has_async("k") is True
    assert await cache.get_async("k") == "v"
    assert await cache.delete_async("k") is True
    assert await cache.has_async("k") is False
