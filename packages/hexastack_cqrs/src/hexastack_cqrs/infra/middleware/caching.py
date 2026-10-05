"""Declarative Query Caching and Command Invalidation Middleware for CQRS Pipelines."""

from __future__ import annotations

import hashlib
import inspect
import json
from collections.abc import Callable
from typing import Any, TypeVar, cast

from hexastack_core.domain import Command, Generic, Query
from hexastack_core.ports.cache import AsyncCachePort, CachePort
from hexastack_cqrs.infra.decorators import (
    _COMMAND_INVALIDATION_META_ATTR,
    _QUERY_CACHE_META_ATTR,
    CommandInvalidationMetadata,
    QueryCacheMetadata,
)

G = TypeVar("G", bound=Generic)
R = TypeVar("R")


def compute_cache_key(query: Query[Any], metadata: QueryCacheMetadata) -> str:
    """Compute a deterministic, collision-free cache key for a Query instance.

    Args:
        query: The Query instance being executed.
        metadata: The QueryCacheMetadata attached via @cached_query.

    Returns:
        A deterministic cache key string.

    Notes/Architectural Intent:
        Uses a custom key builder if provided, explicit key fields if specified,
        or canonical JSON SHA-256 hash of the query model attributes.
    """
    if metadata.key_builder is not None:
        return metadata.key_builder(query)

    class_name = query.__class__.__name__

    if metadata.key_fields:
        field_vals = ":".join(str(getattr(query, f, "")) for f in metadata.key_fields)
        return f"query:{class_name}:{field_vals}"

    if hasattr(query, "model_dump_json"):
        payload_str = query.model_dump_json(exclude_none=True)
    elif hasattr(query, "__dict__"):
        clean_dict = {k: v for k, v in query.__dict__.items() if not k.startswith("_")}
        payload_str = json.dumps(clean_dict, sort_keys=True, default=str)
    else:
        payload_str = str(query)

    payload_hash = hashlib.sha256(payload_str.encode("utf-8")).hexdigest()[:16]
    return f"query:{class_name}:{payload_hash}"


class QueryCachingMiddleware:
    """CQRS pipeline middleware intercepting queries for declarative result caching.

    Notes/Architectural Intent:
        Intercepts Query messages decorated with @cached_query, returning cached
        DTO results on cache hits or delegating to the downstream handler on cache misses.
        Supports both synchronous CachePort and asynchronous AsyncCachePort.
    """

    def __init__(self, cache: CachePort | AsyncCachePort) -> None:
        """Initialize QueryCachingMiddleware with a cache adapter.

        Args:
            cache: CachePort or AsyncCachePort implementation.
        """
        self._cache = cache

    def __call__(self, instance: G, next_call: Callable[[G], R]) -> Any:
        """Intercept query execution, check cache, and populate cache on miss.

        Args:
            instance: Message instance being dispatched.
            next_call: Next callable in the middleware/handler chain.

        Returns:
            Query result (either fresh or cached) or an async coroutine.
        """
        cache_meta: QueryCacheMetadata | None = getattr(
            instance.__class__, _QUERY_CACHE_META_ATTR, None
        )
        if cache_meta is None or not isinstance(instance, Query):
            return next_call(instance)

        cache_key = compute_cache_key(instance, cache_meta)

        if isinstance(self._cache, AsyncCachePort):
            return cast(
                "R", self._handle_async(instance, next_call, cache_key, cache_meta)
            )

        # Synchronous execution flow
        cached_value = self._cache.get(cache_key)
        if cached_value is not None:
            return cast("R", cached_value)

        result = next_call(instance)

        if inspect.iscoroutine(result):
            return cast("R", self._await_and_cache(result, cache_key, cache_meta))

        if result is not None:
            self._cache.set(cache_key, result, ttl_seconds=cache_meta.ttl_seconds)
            # Track tags for group invalidation if tags present
            if cache_meta.tags:
                self._record_tags_sync(cache_key, cache_meta.tags, instance)

        return result

    async def _handle_async(
        self,
        instance: G,
        next_call: Callable[[G], R],
        cache_key: str,
        cache_meta: QueryCacheMetadata,
    ) -> Any:

        async_cache = cast("AsyncCachePort", self._cache)
        cached_val = await async_cache.get_async(cache_key)
        if cached_val is not None:
            return cached_val

        result = next_call(instance)
        if inspect.iscoroutine(result):
            result = await result

        if result is not None:
            await async_cache.set_async(
                cache_key, result, ttl_seconds=cache_meta.ttl_seconds
            )
            if cache_meta.tags:
                await self._record_tags_async(cache_key, cache_meta.tags, instance)

        return result

    async def _await_and_cache(
        self, coro: Any, cache_key: str, cache_meta: QueryCacheMetadata
    ) -> Any:
        result = await coro
        if result is not None:
            cast("CachePort", self._cache).set(
                cache_key, result, ttl_seconds=cache_meta.ttl_seconds
            )
        return result

    def _record_tags_sync(
        self, cache_key: str, tags: tuple[str, ...], instance: Any
    ) -> None:
        sync_cache = cast("CachePort", self._cache)
        for tag_template in tags:
            tag = self._render_tag(tag_template, instance)
            tag_key = f"tag:{tag}"
            existing: set[str] = set(sync_cache.get(tag_key) or [])
            existing.add(cache_key)
            sync_cache.set(tag_key, list(existing))

    async def _record_tags_async(
        self, cache_key: str, tags: tuple[str, ...], instance: Any
    ) -> None:
        async_cache = cast("AsyncCachePort", self._cache)
        for tag_template in tags:
            tag = self._render_tag(tag_template, instance)
            tag_key = f"tag:{tag}"
            existing: set[str] = set(await async_cache.get_async(tag_key) or [])
            existing.add(cache_key)
            await async_cache.set_async(tag_key, list(existing))

    @staticmethod
    def _render_tag(template: str, instance: Any) -> str:
        try:
            if hasattr(instance, "__dict__"):
                return template.format(**instance.__dict__)
            return template
        except Exception:
            return template


class CommandCacheInvalidationMiddleware:
    """CQRS pipeline middleware invalidating cached queries when commands succeed.

    Notes/Architectural Intent:
        Purges cached query keys associated with tags specified in @invalidates_cache.
    """

    def __init__(self, cache: CachePort | AsyncCachePort) -> None:
        """Initialize CommandCacheInvalidationMiddleware with cache adapter."""
        self._cache = cache

    def __call__(self, instance: G, next_call: Callable[[G], R]) -> Any:
        """Intercept command execution and purge tagged cache entries upon success."""
        inval_meta: CommandInvalidationMetadata | None = getattr(
            instance.__class__, _COMMAND_INVALIDATION_META_ATTR, None
        )
        if inval_meta is None or not isinstance(instance, Command):
            return next_call(instance)

        result = next_call(instance)

        if isinstance(self._cache, AsyncCachePort):
            return cast(
                "R", self._handle_async_invalidate(result, inval_meta, instance)
            )

        if inspect.iscoroutine(result):
            return cast("R", self._await_and_invalidate(result, inval_meta, instance))

        self._invalidate_tags_sync(inval_meta.tags, instance)
        return result

    async def _handle_async_invalidate(
        self, result: Any, inval_meta: CommandInvalidationMetadata, instance: Any
    ) -> Any:
        if inspect.iscoroutine(result):
            result = await result
        await self._invalidate_tags_async(inval_meta.tags, instance)
        return result

    async def _await_and_invalidate(
        self, coro: Any, inval_meta: CommandInvalidationMetadata, instance: Any
    ) -> Any:
        result = await coro
        await self._invalidate_tags_async(inval_meta.tags, instance)
        return result

    def _invalidate_tags_sync(self, tags: tuple[str, ...], instance: Any) -> None:
        if not isinstance(self._cache, CachePort):
            return
        for tag_template in tags:
            tag = QueryCachingMiddleware._render_tag(tag_template, instance)
            tag_key = f"tag:{tag}"
            keys_to_delete = self._cache.get(tag_key)
            if keys_to_delete:
                for k in keys_to_delete:
                    self._cache.delete(k)
                self._cache.delete(tag_key)

    async def _invalidate_tags_async(
        self, tags: tuple[str, ...], instance: Any
    ) -> None:
        if not isinstance(self._cache, AsyncCachePort):
            return
        for tag_template in tags:
            tag = QueryCachingMiddleware._render_tag(tag_template, instance)
            tag_key = f"tag:{tag}"
            keys_to_delete = await self._cache.get_async(tag_key)
            if keys_to_delete:
                for k in keys_to_delete:
                    await self._cache.delete_async(k)
                await self._cache.delete_async(tag_key)
