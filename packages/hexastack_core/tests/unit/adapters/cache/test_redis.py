import fakeredis
import fakeredis.aioredis
import pytest

from hexastack_core.adapters.cache.redis import (
    AsyncRedisCacheAdapter,
    RedisCacheAdapter,
    _deserialize_value,
    _serialize_value,
)


def test_value_serialization_and_deserialization():
    # String
    s_raw = _serialize_value("hello")
    assert _deserialize_value(s_raw) == "hello"

    # Bytes
    b_raw = _serialize_value(b"binary data")
    assert _deserialize_value(b_raw) == b"binary data"

    # Dict / JSON
    d_raw = _serialize_value({"key": "val", "num": 123})
    assert _deserialize_value(d_raw) == {"key": "val", "num": 123}

    # None and fallback defaults
    assert _deserialize_value(None, default="fallback") == "fallback"
    assert _deserialize_value("invalid-json{", default="fallback") == "invalid-json{"


def test_sync_redis_cache_adapter_crud():
    fake_client = fakeredis.FakeRedis()
    cache = RedisCacheAdapter(client=fake_client, key_prefix="app:")

    # Initial state
    assert cache.has("user:1") is False
    assert cache.get("user:1", "default_val") == "default_val"

    # Set and Get
    cache.set("user:1", {"id": 1, "name": "Alice"})
    assert cache.has("user:1") is True
    assert cache.get("user:1") == {"id": 1, "name": "Alice"}

    # Delete
    deleted = cache.delete("user:1")
    assert deleted is True
    assert cache.has("user:1") is False
    deleted_again = cache.delete("user:1")
    assert deleted_again is False

    # Clear with prefix
    cache.set("item:1", "apple")
    cache.set("item:2", "banana")
    cache.clear()
    assert cache.has("item:1") is False
    assert cache.has("item:2") is False

    # Clear empty prefix
    cache.clear()

    # Clear without prefix
    no_prefix_cache = RedisCacheAdapter(client=fake_client)
    no_prefix_cache.set("plain_key", "value")
    assert no_prefix_cache.has("plain_key") is True

    no_prefix_cache.clear()
    assert no_prefix_cache.has("plain_key") is False


def test_sync_redis_cache_adapter_ttl():
    fake_client = fakeredis.FakeRedis()
    cache = RedisCacheAdapter(client=fake_client)

    cache.set("temp_key", "temp_value", ttl_seconds=0.1)
    assert cache.has("temp_key") is True
    assert cache.get("temp_key") == "temp_value"

    # Fast forward time on fakeredis
    fake_client.time()
    # Expire via ttl
    fake_client.expire("temp_key", 0)
    assert cache.has("temp_key") is False
    assert cache.get("temp_key") is None


@pytest.mark.asyncio
async def test_async_redis_cache_adapter_crud():
    fake_async_client = fakeredis.aioredis.FakeRedis()
    cache = AsyncRedisCacheAdapter(client=fake_async_client, key_prefix="async_app:")

    # Initial state
    assert await cache.has_async("user:2") is False
    assert await cache.get_async("user:2", "fallback") == "fallback"

    # Set and Get
    await cache.set_async("user:2", {"id": 2, "role": "admin"})
    assert await cache.has_async("user:2") is True
    assert await cache.get_async("user:2") == {"id": 2, "role": "admin"}

    # Delete
    deleted = await cache.delete_async("user:2")
    assert deleted is True
    assert await cache.has_async("user:2") is False
    deleted_again = await cache.delete_async("user:2")
    assert deleted_again is False

    # Clear with prefix
    await cache.set_async("msg:1", "hello")
    await cache.set_async("msg:2", "world")
    await cache.clear_async()
    assert await cache.has_async("msg:1") is False
    assert await cache.has_async("msg:2") is False

    # Clear empty prefix
    await cache.clear_async()

    # Clear without prefix
    no_prefix_cache = AsyncRedisCacheAdapter(client=fake_async_client)
    await no_prefix_cache.set_async("global_k", "global_v")
    assert await no_prefix_cache.has_async("global_k") is True

    await no_prefix_cache.clear_async()
    assert await no_prefix_cache.has_async("global_k") is False


@pytest.mark.asyncio
async def test_async_redis_cache_adapter_ttl():
    fake_async_client = fakeredis.aioredis.FakeRedis()
    cache = AsyncRedisCacheAdapter(client=fake_async_client)

    await cache.set_async("async_temp", "val", ttl_seconds=0.1)
    assert await cache.has_async("async_temp") is True
    assert await cache.get_async("async_temp") == "val"

    await fake_async_client.expire("async_temp", 0)
    assert await cache.has_async("async_temp") is False
    assert await cache.get_async("async_temp") is None
