"""Unit tests for type-safe sync/async concurrency utilities.

Notes/Architectural Intent:
    Verifies context variable preservation, exception propagation, and structured
    concurrency bridging across async and sync thread boundaries.
"""

from __future__ import annotations

import asyncio
import contextvars
import functools
import inspect
import threading
from unittest.mock import patch

import pytest

import hexastack_core
import hexastack_core.utils as hexastack_utils
from hexastack_core.exceptions import MissingDependencyError
from hexastack_core.utils.concurrency import (
    asyncify,
    auto_async,
    create_task_group,
    is_coroutine_callable,
    runnify,
    syncify,
    to_async,
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


@pytest.mark.anyio
async def test_to_async_decorator_and_functional_usage() -> None:
    """Verify to_async exposes a true coroutine function and offloads to a thread."""
    caller_thread = threading.get_ident()

    @to_async
    def blocking_add(x: int, y: int = 10) -> tuple[int, int]:
        """Add two integers synchronously."""
        return x + y, threading.get_ident()

    def plain_multiply(a: int, b: int) -> int:
        return a * b

    is_coro_decorated = inspect.iscoroutinefunction(blocking_add)
    assert is_coro_decorated is True
    assert blocking_add.__name__ == "blocking_add"
    assert blocking_add.__doc__ == "Add two integers synchronously."
    assert callable(getattr(blocking_add, "__wrapped__", None))

    total, worker_thread = await blocking_add(5, y=7)
    assert total == 12
    assert worker_thread != caller_thread

    wrapped_plain = to_async(plain_multiply)
    is_coro_plain = inspect.iscoroutinefunction(wrapped_plain)
    assert is_coro_plain is True
    product = await wrapped_plain(4, 9)
    assert product == 36


@pytest.mark.anyio
async def test_to_async_preserves_contextvars_and_propagates_exceptions() -> None:
    """Verify to_async forwards contextvars and propagates sync exceptions."""
    token = test_ctx_var.set("to_async_ctx")
    try:

        @to_async
        def read_ctx_or_fail(should_fail: bool) -> str:
            if should_fail:
                raise CustomConcurrencyError("sync explosion")
            return test_ctx_var.get()

        ctx_value = await read_ctx_or_fail(False)
        assert ctx_value == "to_async_ctx"

        with pytest.raises(CustomConcurrencyError, match="sync explosion"):
            await read_ctx_or_fail(True)
    finally:
        test_ctx_var.reset(token)


@pytest.mark.anyio
async def test_to_async_wasm_cooperative_fallback() -> None:
    """Verify to_async runs cooperatively in-loop when supports_threads() is False."""
    main_thread = threading.get_ident()

    @to_async
    def sync_step(value: str) -> tuple[str, int]:
        return f"coop:{value}", threading.get_ident()

    with patch("hexastack_core.utils.concurrency.supports_threads", return_value=False):
        output, exec_thread = await sync_step("edge")

    assert output == "coop:edge"
    assert exec_thread == main_thread


@pytest.mark.anyio
async def test_to_async_idempotent_on_coroutine_function() -> None:
    """Verify to_async returns coroutine functions directly without wrapping."""

    async def already_async(val: int) -> int:
        await asyncio.sleep(0)
        return val + 1

    wrapped = to_async(already_async)
    assert wrapped is already_async
    res = await wrapped(41)
    assert res == 42


@pytest.mark.anyio
async def test_auto_async_bare_decorator() -> None:
    """Verify bare @auto_async creates async twins while skipping non-sync-method members."""
    property_accessed = False

    def dotless_op(self: object) -> str:
        return "dotless"

    dotless_op.__qualname__ = "dotless_op"

    @auto_async
    class SampleClient:
        class_const = "const_value"
        dotless = dotless_op

        def __init__(self, factor: int) -> None:
            self.factor = factor

        def _internal(self) -> str:
            return "private"

        @property
        def dangerous_prop(self) -> str:
            nonlocal property_accessed
            property_accessed = True
            return "prop"

        def compute(self, value: int) -> int:
            return value * self.factor

        async def native_async(self, text: str) -> str:
            await asyncio.sleep(0)
            return f"native:{text}"

    assert property_accessed is False
    has_compute_async = hasattr(SampleClient, "compute_async")
    has_dotless_async = hasattr(SampleClient, "dotless_async")
    has_internal_async = hasattr(SampleClient, "_internal_async")
    has_prop_async = hasattr(SampleClient, "dangerous_prop_async")
    has_native_double = hasattr(SampleClient, "native_async_async")
    has_const_async = hasattr(SampleClient, "class_const_async")
    assert has_compute_async is True
    assert has_dotless_async is True
    assert has_internal_async is False
    assert has_prop_async is False
    assert has_native_double is False
    assert has_const_async is False

    compute_attr = SampleClient.compute_async  # ty: ignore[unresolved-attribute]
    dotless_attr = SampleClient.dotless_async  # ty: ignore[unresolved-attribute]
    compute_qual_ok = compute_attr.__qualname__.endswith("SampleClient.compute_async")
    dotless_qual = dotless_attr.__qualname__
    assert compute_qual_ok is True
    assert dotless_qual == "dotless_async"

    client = SampleClient(factor=3)
    compute_async = client.compute_async  # ty: ignore[unresolved-attribute]
    dotless_async = client.dotless_async  # ty: ignore[unresolved-attribute]
    res = await compute_async(7)
    dotless_res = await dotless_async()
    native_res = await client.native_async("ok")
    assert res == 21
    assert dotless_res == "dotless"
    assert native_res == "native:ok"


@pytest.mark.anyio
async def test_auto_async_parameterized_suffix_and_exclude() -> None:
    """Verify @auto_async honors custom suffix and exclude parameters."""

    @auto_async(suffix="_bg", exclude=("close",))
    class DbDriver:
        def query(self, sql: str) -> str:
            return f"ran:{sql}"

        def close(self) -> str:
            return "closed"

    has_query_bg = hasattr(DbDriver, "query_bg")
    has_close_bg = hasattr(DbDriver, "close_bg")
    has_query_async = hasattr(DbDriver, "query_async")
    assert has_query_bg is True
    assert has_close_bg is False
    assert has_query_async is False

    driver = DbDriver()
    query_bg = driver.query_bg  # ty: ignore[unresolved-attribute]
    res = await query_bg("SELECT 1")
    sync_closed = driver.close()
    assert res == "ran:SELECT 1"
    assert sync_closed == "closed"


@pytest.mark.anyio
async def test_auto_async_never_overwrites_explicit_async_method() -> None:
    """Verify @auto_async leaves handwritten and inherited async twins untouched."""

    class BaseAsyncClient:
        async def base_op_async(self) -> str:
            await asyncio.sleep(0)
            return "inherited_explicit"

    @auto_async
    class CustomAsyncClient(BaseAsyncClient):
        def fetch(self, key: str) -> str:
            return f"sync:{key}"

        async def fetch_async(self, key: str) -> str:
            await asyncio.sleep(0)
            return f"explicit:{key}"

        def base_op(self) -> str:
            return "sync_base"

    client = CustomAsyncClient()
    sync_res = client.fetch("abc")
    async_res = await client.fetch_async("abc")
    inherited_async_res = await client.base_op_async()
    assert sync_res == "sync:abc"
    assert async_res == "explicit:abc"
    assert inherited_async_res == "inherited_explicit"


@pytest.mark.anyio
async def test_auto_async_loop_closure_isolation_and_contextvars() -> None:
    """Verify multiple generated twins bind distinct sync methods without loop capture bugs."""

    @auto_async
    class MultiOpClient:
        def __init__(self, prefix: str) -> None:
            self.prefix = prefix

        def op_alpha(self) -> str:
            return f"{self.prefix}:alpha:{test_ctx_var.get()}"

        def op_beta(self) -> str:
            return f"{self.prefix}:beta:{test_ctx_var.get()}"

        def op_gamma(self) -> str:
            return f"{self.prefix}:gamma:{test_ctx_var.get()}"

    token = test_ctx_var.set("isolated")
    try:
        client = MultiOpClient(prefix="svc")
        op_alpha_async = client.op_alpha_async  # ty: ignore[unresolved-attribute]
        op_beta_async = client.op_beta_async  # ty: ignore[unresolved-attribute]
        op_gamma_async = client.op_gamma_async  # ty: ignore[unresolved-attribute]
        res_a = await op_alpha_async()
        res_b = await op_beta_async()
        res_c = await op_gamma_async()
        assert res_a == "svc:alpha:isolated"
        assert res_b == "svc:beta:isolated"
        assert res_c == "svc:gamma:isolated"
    finally:
        test_ctx_var.reset(token)


@pytest.mark.anyio
async def test_auto_async_staticmethod_and_classmethod() -> None:
    """Verify @auto_async wraps sync staticmethod and classmethod and skips async ones."""

    @auto_async
    class DescriptorClient:
        label = "descriptor"

        @staticmethod
        def ping(tag: str) -> str:
            return f"pong:{tag}"

        @staticmethod
        async def async_ping(tag: str) -> str:
            return f"apong:{tag}"

        @classmethod
        def describe(cls, detail: str) -> str:
            return f"{cls.label}:{detail}"

        @classmethod
        async def async_describe(cls, detail: str) -> str:
            return f"async:{cls.label}:{detail}"

    has_ping_async = hasattr(DescriptorClient, "ping_async")
    has_describe_async = hasattr(DescriptorClient, "describe_async")
    has_async_ping_async = hasattr(DescriptorClient, "async_ping_async")
    has_async_describe_async = hasattr(DescriptorClient, "async_describe_async")
    assert has_ping_async is True
    assert has_describe_async is True
    assert has_async_ping_async is False
    assert has_async_describe_async is False

    ping_async = DescriptorClient.ping_async  # ty: ignore[unresolved-attribute]
    describe_async = DescriptorClient.describe_async  # ty: ignore[unresolved-attribute]
    ping_res = await ping_async("v1")
    desc_res = await describe_async("ok")
    assert ping_res == "pong:v1"
    assert desc_res == "descriptor:ok"


def test_auto_async_empty_suffix_raises_value_error() -> None:
    """Verify auto_async rejects empty suffix values."""
    with pytest.raises(ValueError, match="non-empty"):
        auto_async(suffix="")


def test_public_exports_in_hexastack_core_and_utils() -> None:
    """Verify to_async and auto_async are exported by hexastack_core and hexastack_core.utils."""
    assert hexastack_core.to_async is to_async
    assert hexastack_core.auto_async is auto_async
    assert hexastack_utils.to_async is to_async
    assert hexastack_utils.auto_async is auto_async
    has_core_to = "to_async" in hexastack_core.__all__
    has_core_auto = "auto_async" in hexastack_core.__all__
    has_utils_to = "to_async" in hexastack_utils.__all__
    has_utils_auto = "auto_async" in hexastack_utils.__all__
    assert has_core_to is True
    assert has_core_auto is True
    assert has_utils_to is True
    assert has_utils_auto is True
