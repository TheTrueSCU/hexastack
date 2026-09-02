import tempfile
import time

import pytest

from hexastack_core.adapters.cache.disk import (
    AsyncDiskCacheAdapter,
    DiskCacheAdapter,
)


def test_disk_cache_adapter_sync_lifecycle():
    with tempfile.TemporaryDirectory() as tmpdir:
        cache = DiskCacheAdapter(directory=tmpdir)

        assert cache.has("user:1") is False
        assert cache.get("user:1") is None
        assert cache.get("user:1", default="guest") == "guest"

        # Set value
        cache.set("user:1", {"name": "Alice", "role": "admin"})
        assert cache.has("user:1") is True
        assert cache.get("user:1") == {"name": "Alice", "role": "admin"}

        # Delete
        assert cache.delete("user:1") is True
        assert cache.has("user:1") is False
        assert cache.delete("user:1") is False

        # TTL expiration
        cache.set("temp:key", "value", ttl_seconds=0.1)
        assert cache.has("temp:key") is True
        time.sleep(0.15)
        assert cache.has("temp:key") is False
        assert cache.get("temp:key") is None

        # Clear
        cache.set("k1", "v1")
        cache.set("k2", "v2")
        cache.clear()
        assert cache.has("k1") is False
        assert cache.has("k2") is False

        cache.close()


def test_disk_cache_adapter_persistence_across_instances():
    with tempfile.TemporaryDirectory() as tmpdir:
        # Instance 1 writes
        cache1 = DiskCacheAdapter(directory=tmpdir)
        cache1.set("persisted:key", [1, 2, 3])
        cache1.close()

        # Instance 2 reads from same directory
        cache2 = DiskCacheAdapter(directory=tmpdir)
        assert cache2.has("persisted:key") is True
        assert cache2.get("persisted:key") == [1, 2, 3]
        cache2.close()


@pytest.mark.anyio
async def test_async_disk_cache_adapter_lifecycle():
    with tempfile.TemporaryDirectory() as tmpdir:
        cache = AsyncDiskCacheAdapter(directory=tmpdir)

        assert await cache.has_async("async:key") is False
        assert await cache.get_async("async:key", default="empty") == "empty"

        await cache.set_async("async:key", "async_value")
        assert await cache.has_async("async:key") is True
        assert await cache.get_async("async:key") == "async_value"

        assert await cache.delete_async("async:key") is True
        assert await cache.has_async("async:key") is False

        await cache.set_async("k1", "v1")
        await cache.clear_async()
        assert await cache.has_async("k1") is False

        await cache.close_async()


def test_disk_cache_adapter_missing_dependency(monkeypatch):
    import sys

    from hexastack_core.domain.exceptions import MissingDependencyError

    monkeypatch.setitem(sys.modules, "diskcache", None)
    with pytest.raises(MissingDependencyError):
        DiskCacheAdapter()
