"""Unit tests for type-safe sync/async concurrency utilities.

Notes/Architectural Intent:
    Verifies context variable preservation, exception propagation, and structured
    concurrency bridging across async and sync thread boundaries.
"""

from __future__ import annotations

import contextvars
import functools
from unittest.mock import patch

import pytest

from hexastack_core.exceptions import MissingDependencyError
from hexastack_core.utils.concurrency import (
    asyncify,
    create_task_group,
    is_coroutine_callable,
    runnify,
    syncify,
)

test_ctx_var: contextvars.ContextVar[str] = contextvars.ContextVar(
    "test_ctx_var", default="initial"
)


class CustomConcurrencyError(Exception):
    """Custom error for testing exception propagation."""


def test_is_coroutine_callable() -> None:
    """Verify is_coroutine_callable correctly detects async and sync callables."""

    async def async_fn() -> str:
        return "async"

    def sync_fn() -> str:
        return "sync"

    @functools.wraps(async_fn)
    def wrapped_async() -> str:
        return "wrapped"

    class AsyncCallableClass:
        async def __call__(self) -> str:
            return "callable_async"

    class SyncCallableClass:
        def __call__(self) -> str:
            return "callable_sync"

    res_async = is_coroutine_callable(async_fn)
    assert res_async is True

    res_sync = is_coroutine_callable(sync_fn)
    assert res_sync is False

    res_wrapped = is_coroutine_callable(wrapped_async)
    assert res_wrapped is True

    res_obj_async = is_coroutine_callable(AsyncCallableClass())
    assert res_obj_async is True

    res_obj_sync = is_coroutine_callable(SyncCallableClass())
    assert res_obj_sync is False


@pytest.mark.anyio
async def test_asyncify_executes_and_preserves_context() -> None:
    """Verify asyncify executes sync work on thread with context variable propagation."""
    test_ctx_var.set("parent_context_val")

    def sync_worker(prefix: str, multiplier: int) -> str:
        current_ctx = test_ctx_var.get()
        return f"{prefix}_{multiplier}_{current_ctx}"

    async_worker = asyncify(sync_worker)
    res = await async_worker("item", 3)
    assert res == "item_3_parent_context_val"


@pytest.mark.anyio
async def test_asyncify_propagates_exceptions() -> None:
    """Verify asyncify propagates exceptions raised inside sync work."""

    def failing_worker() -> None:
        raise CustomConcurrencyError("failure in thread")

    async_worker = asyncify(failing_worker)
    with pytest.raises(CustomConcurrencyError, match="failure in thread"):
        await async_worker()


@pytest.mark.anyio
async def test_asyncify_fallback_without_asyncer() -> None:
    """Verify asyncify fallback path operates when asyncer is unavailable."""
    test_ctx_var.set("fallback_ctx")

    def sync_work(val: int) -> int:
        assert test_ctx_var.get() == "fallback_ctx"
        return val * 10

    with patch(
        "hexastack_core.utils.concurrency.optional_dependency", return_value=None
    ):
        fallback_fn = asyncify(sync_work)
        res = await fallback_fn(5)
        assert res == 50


@pytest.mark.anyio
async def test_syncify_inside_asyncify_thread() -> None:
    """Verify syncify calls async function from inside offloaded thread worker."""

    async def fetch_async(val: str) -> str:
        return f"remote_{val}"

    def sync_pipeline_step(val: str) -> str:
        sync_fetch = syncify(fetch_async)
        fetched = sync_fetch(val)
        return f"processed_{fetched}"

    res = await asyncify(sync_pipeline_step)("alpha")
    assert res == "processed_remote_alpha"


def test_syncify_missing_dependency() -> None:
    """Verify syncify raises MissingDependencyError when asyncer is missing."""

    async def dummy() -> None:
        pass

    with (
        patch(
            "hexastack_core.utils.concurrency.require_dependency",
            side_effect=MissingDependencyError("asyncer missing"),
        ),
        pytest.raises(MissingDependencyError, match="asyncer missing"),
    ):
        syncify(dummy)


@pytest.mark.anyio
async def test_create_task_group_structured_concurrency() -> None:
    """Verify create_task_group executes child tasks under structured concurrency."""
    results: list[int] = []

    async def task_worker(val: int) -> None:
        results.append(val)

    async with create_task_group() as tg:
        tg.soonify(task_worker)(1)
        tg.soonify(task_worker)(2)

    assert sorted(results) == [1, 2]


def test_create_task_group_missing_dependency() -> None:
    """Verify create_task_group raises MissingDependencyError when asyncer is missing."""
    with (
        patch(
            "hexastack_core.utils.concurrency.require_dependency",
            side_effect=MissingDependencyError("asyncer missing"),
        ),
        pytest.raises(MissingDependencyError, match="asyncer missing"),
    ):
        create_task_group()


def test_runnify_executes_coroutine() -> None:
    """Verify runnify synchronously executes async coroutine to completion."""

    async def compute(a: int, b: int) -> int:
        return a + b

    sync_compute = runnify(compute)
    res = sync_compute(10, 20)
    assert res == 30


def test_runnify_fallback_without_asyncer() -> None:
    """Verify runnify fallback uses asyncio.run when asyncer is unavailable."""

    async def compute(a: int, b: int) -> int:
        return a * b

    with patch(
        "hexastack_core.utils.concurrency.optional_dependency", return_value=None
    ):
        sync_compute = runnify(compute)
        res = sync_compute(6, 7)
        assert res == 42
