from typing import Any

import pytest

from hexastack_core.adapters.cache.in_memory import (
    AsyncInMemoryCache,
    InMemoryCache,
)
from hexastack_core.domain import Command, Query
from hexastack_cqrs.infra.decorators import cached_query, invalidates_cache
from hexastack_cqrs.infra.middleware.caching import (
    CommandCacheInvalidationMiddleware,
    QueryCachingMiddleware,
)


@cached_query(ttl_seconds=60, tags=["users", "user:{user_id}"])
class GetUserQuery(Query):
    user_id: str


@cached_query(ttl_seconds=30, key_fields=["category"])
class ListItemsQuery(Query):
    category: str
    page: int = 1


@cached_query(key_builder=lambda q: f"custom:{q.user_id}")
class GetUserCustomQuery(Query):
    user_id: str


@invalidates_cache(tags=["users", "user:{user_id}"])
class UpdateUserCommand(Command):
    user_id: str
    name: str


def test_query_caching_sync_flow() -> None:
    cache = InMemoryCache()
    query_mw = QueryCachingMiddleware(cache)
    inval_mw = CommandCacheInvalidationMiddleware(cache)

    calls = 0

    def query_handler(q: GetUserQuery) -> dict[str, Any]:
        nonlocal calls
        calls += 1
        return {"id": q.user_id, "name": f"User {q.user_id}"}

    query = GetUserQuery(user_id="42")

    # 1. First execution -> Miss, calls handler
    res1 = query_mw(query, query_handler)
    assert res1 == {"id": "42", "name": "User 42"}
    assert calls == 1

    # 2. Second execution -> Hit, handler not called
    res2 = query_mw(query, query_handler)
    assert res2 == {"id": "42", "name": "User 42"}
    assert calls == 1

    # 3. Execute invalidation command
    cmd = UpdateUserCommand(user_id="42", name="Updated")
    inval_mw(cmd, lambda _: None)

    # 4. Third execution -> Miss again because cache was invalidated
    res3 = query_mw(query, query_handler)
    assert res3 == {"id": "42", "name": "User 42"}
    assert calls == 2


def test_query_caching_key_builder_and_fields() -> None:
    cache = InMemoryCache()
    query_mw = QueryCachingMiddleware(cache)

    q1 = ListItemsQuery(category="books", page=1)
    q2 = ListItemsQuery(category="books", page=2)

    # Since key_fields is ["category"], q1 and q2 share the same key
    query_mw(q1, lambda _: "cached_books")
    assert query_mw(q2, lambda _: "fresh") == "cached_books"

    q_custom = GetUserCustomQuery(user_id="99")
    query_mw(q_custom, lambda _: "user_99")
    assert cache.get("custom:99") == "user_99"


@pytest.mark.anyio
async def test_query_caching_async_flow() -> None:
    cache = AsyncInMemoryCache()
    query_mw = QueryCachingMiddleware(cache)
    inval_mw = CommandCacheInvalidationMiddleware(cache)

    calls = 0

    async def async_handler(q: GetUserQuery) -> dict[str, Any]:
        nonlocal calls
        calls += 1
        return {"id": q.user_id, "name": f"Async {q.user_id}"}

    query = GetUserQuery(user_id="100")

    # 1. Async miss
    res1 = await query_mw(query, async_handler)
    assert res1 == {"id": "100", "name": "Async 100"}
    assert calls == 1

    # 2. Async hit
    res2 = await query_mw(query, async_handler)
    assert res2 == {"id": "100", "name": "Async 100"}
    assert calls == 1

    # 3. Async Invalidate
    cmd = UpdateUserCommand(user_id="100", name="Async Updated")
    await inval_mw(cmd, lambda _: None)

    # 4. Async miss after invalidation
    res3 = await query_mw(query, async_handler)
    assert res3 == {"id": "100", "name": "Async 100"}
    assert calls == 2
