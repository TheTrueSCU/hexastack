import asyncio

import pytest

from hexastack_core.domain import Command
from hexastack_core.utils.context import (
    correlation_id_ctx,
    get_correlation_id,
    set_correlation_id,
)
from hexastack_cqrs.infra.middleware.correlation import CorrelationMiddleware


class _CmdWithCid(Command):
    correlation_id: str
    name: str


class _CmdWithoutCid(Command):
    name: str


def test_correlation_middleware_extracts_existing_cid():
    set_correlation_id("")
    middleware = CorrelationMiddleware()

    captured_cid = ""

    def handler(cmd: _CmdWithCid) -> str:
        nonlocal captured_cid
        captured_cid = get_correlation_id()
        return "ok"

    cmd = _CmdWithCid(correlation_id="explicit-cid-123", name="test")
    res = middleware(cmd, handler)

    assert res == "ok"
    assert captured_cid == "explicit-cid-123"


def test_correlation_middleware_generates_when_missing():
    set_correlation_id("")
    middleware = CorrelationMiddleware(generate_if_missing=True)

    captured_cid = ""

    def handler(cmd: _CmdWithoutCid) -> str:
        nonlocal captured_cid
        captured_cid = get_correlation_id()
        return "ok"

    cmd = _CmdWithoutCid(name="test")
    res = middleware(cmd, handler)

    assert res == "ok"
    assert len(captured_cid) > 0
    assert captured_cid != ""


def test_correlation_middleware_preserves_existing_context():
    set_correlation_id("pre-existing-cid")
    middleware = CorrelationMiddleware()

    captured_cid = ""

    def handler(cmd: _CmdWithoutCid) -> str:
        nonlocal captured_cid
        captured_cid = get_correlation_id()
        return "ok"

    cmd = _CmdWithoutCid(name="test")
    res = middleware(cmd, handler)

    assert res == "ok"
    assert captured_cid == "pre-existing-cid"
    correlation_id_ctx.set("")


@pytest.mark.anyio
async def test_correlation_middleware_async():
    set_correlation_id("")
    middleware = CorrelationMiddleware()

    captured_cid = ""

    async def async_handler(cmd: _CmdWithCid) -> str:
        nonlocal captured_cid
        await asyncio.sleep(0.01)
        captured_cid = get_correlation_id()
        return "async-ok"

    cmd = _CmdWithCid(correlation_id="async-cid-999", name="async-test")
    coro = middleware(cmd, async_handler)
    res = await coro

    assert res == "async-ok"
    assert captured_cid == "async-cid-999"
    correlation_id_ctx.set("")
