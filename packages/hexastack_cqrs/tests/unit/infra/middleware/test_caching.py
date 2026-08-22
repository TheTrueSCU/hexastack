"""Unit tests for CQRS QueryCachingMiddleware and CommandCacheInvalidationMiddleware."""

from typing import Any

from hexastack_core.adapters.cache.in_memory import InMemoryCache
from hexastack_core.domain import Command, Query
from hexastack_cqrs.infra.decorators import cached_query, invalidates_cache
from hexastack_cqrs.infra.middleware.caching import (
    CommandCacheInvalidationMiddleware,
    QueryCachingMiddleware,
)


@cached_query(ttl_seconds=60, tags=["users", "user:{user_id}"])
class GetUserQuery(Query):
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
