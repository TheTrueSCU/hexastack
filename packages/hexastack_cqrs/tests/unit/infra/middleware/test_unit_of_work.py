import asyncio

import pytest

from hexastack_core.adapters.unit_of_work import InMemoryUnitOfWork
from hexastack_core.domain import Command
from hexastack_cqrs.infra.middleware.unit_of_work import UnitOfWorkMiddleware


class _SampleCommand(Command):
    name: str


@pytest.mark.anyio
async def test_uow_middleware_async_failure():
    uow = InMemoryUnitOfWork()
    middleware = UnitOfWorkMiddleware(uow=uow)

    async def async_failing_handler(cmd: _SampleCommand) -> str:
        await asyncio.sleep(0.01)
        raise RuntimeError("async fail")

    coro = middleware(_SampleCommand(name="async-fail-cmd"), async_failing_handler)

    with pytest.raises(RuntimeError, match="async fail"):
        await coro

    assert uow.rolled_back is True
    assert uow.rollback_count == 1


@pytest.mark.anyio
async def test_uow_middleware_async_success():
    uow = InMemoryUnitOfWork()
    middleware = UnitOfWorkMiddleware(uow=uow)

    async def async_handler(cmd: _SampleCommand) -> str:
        await asyncio.sleep(0.01)
        return f"async {cmd.name}"

    coro = middleware(_SampleCommand(name="async-cmd"), async_handler)
    res = await coro

    assert res == "async async-cmd"
    assert uow.committed is True
    assert uow.commit_count == 1


def test_uow_middleware_factory():
    instances: list[InMemoryUnitOfWork] = []

    def factory() -> InMemoryUnitOfWork:
        uow = InMemoryUnitOfWork()
        instances.append(uow)
        return uow

    middleware = UnitOfWorkMiddleware(uow=factory)
    middleware(_SampleCommand(name="call1"), lambda c: "ok1")
    middleware(_SampleCommand(name="call2"), lambda c: "ok2")

    assert len(instances) == 2
    assert instances[0].committed is True
    assert instances[1].committed is True


def test_uow_middleware_sync_failure():
    uow = InMemoryUnitOfWork()
    middleware = UnitOfWorkMiddleware(uow=uow)

    def failing_handler(cmd: _SampleCommand) -> str:
        raise ValueError("handler failed")

    with pytest.raises(ValueError, match="handler failed"):
        middleware(_SampleCommand(name="cmd2"), failing_handler)

    assert uow.rolled_back is True
    assert uow.rollback_count == 1
    assert uow.committed is False


def test_uow_middleware_sync_success():
    uow = InMemoryUnitOfWork()
    middleware = UnitOfWorkMiddleware(uow=uow)

    def handler(cmd: _SampleCommand) -> str:
        return f"done {cmd.name}"

    res = middleware(_SampleCommand(name="cmd1"), handler)
    assert res == "done cmd1"
    assert uow.committed is True
    assert uow.commit_count == 1
    assert uow.rolled_back is False
