from collections.abc import Callable
from typing import Any

import pytest

from hexastack_core.domain import Command, Generic
from hexastack_cqrs.infra.middleware.generic import GenericMiddleware, InOutMiddleware


class SampleCommand(Command):
    text: str


class PassThroughMiddleware:
    def __init__(self) -> None:
        self.invoked = False

    def __call__[G: Generic, R](self, instance: G, next_call: Callable[[G], R]) -> R:
        self.invoked = True
        return next_call(instance)


def test_generic_middleware_protocol():
    middleware: GenericMiddleware = PassThroughMiddleware()

    def handler(cmd: SampleCommand) -> str:
        return f"hello {cmd.text}"

    res = middleware(SampleCommand(text="world"), handler)
    assert res == "hello world"


class TrackingInOutMiddleware(InOutMiddleware):
    def __init__(self) -> None:
        self.events: list[str] = []

    def before(self, instance: Generic) -> Any:
        self.events.append(f"before:{instance.__class__.__name__}")
        return {"ctx_id": 42}

    def after(self, instance: Generic, result: Any, context: Any) -> Any:
        self.events.append(f"after:{result}:{context['ctx_id']}")
        return f"wrapped({result})"

    def on_error(self, instance: Generic, exc: Exception, context: Any) -> None:
        self.events.append(f"error:{exc}:{context['ctx_id']}")


def test_in_out_middleware_sync_success():
    mw = TrackingInOutMiddleware()

    def handler(cmd: SampleCommand) -> str:
        return f"processed {cmd.text}"

    res = mw(SampleCommand(text="test"), handler)
    assert res == "wrapped(processed test)"
    assert mw.events == [
        "before:SampleCommand",
        "after:processed test:42",
    ]


def test_in_out_middleware_sync_error():
    mw = TrackingInOutMiddleware()

    def handler(cmd: SampleCommand) -> str:
        raise ValueError("sync failure")

    with pytest.raises(ValueError, match="sync failure"):
        mw(SampleCommand(text="test"), handler)

    assert mw.events == [
        "before:SampleCommand",
        "error:sync failure:42",
    ]


@pytest.mark.asyncio
async def test_in_out_middleware_async_success():
    mw = TrackingInOutMiddleware()

    async def handler(cmd: SampleCommand) -> str:
        return f"async processed {cmd.text}"

    res = await mw(SampleCommand(text="async_test"), handler)
    assert res == "wrapped(async processed async_test)"
    assert mw.events == [
        "before:SampleCommand",
        "after:async processed async_test:42",
    ]


@pytest.mark.asyncio
async def test_in_out_middleware_async_error():
    mw = TrackingInOutMiddleware()

    async def handler(cmd: SampleCommand) -> str:
        raise RuntimeError("async failure")

    with pytest.raises(RuntimeError, match="async failure"):
        await mw(SampleCommand(text="async_test"), handler)

    assert mw.events == [
        "before:SampleCommand",
        "error:async failure:42",
    ]


def test_default_in_out_middleware_hooks():
    mw = InOutMiddleware()
    cmd = SampleCommand(text="default")
    assert mw.before(cmd) is None
    assert mw.after(cmd, "res", None) == "res"
    # on_error should be a safe no-op
    mw.on_error(cmd, ValueError("ignored"), None)
    res = mw(cmd, lambda c: "ok")
    assert res == "ok"
