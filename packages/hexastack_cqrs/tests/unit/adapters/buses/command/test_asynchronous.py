from concurrent.futures import ThreadPoolExecutor
from unittest.mock import patch

import pytest
from huey import MemoryHuey

from hexastack_core.domain import Command
from hexastack_core.domain.exceptions import MissingDependencyError
from hexastack_cqrs.adapters.buses.command.asynchronous import (
    HueyCommandBus,
    NativeAsyncCommandBus,
)
from hexastack_cqrs.infra.registries.handler import HandlerRegistry


class SendEmail(Command):
    recipient: str


def test_huey_command_bus_with_middleware():
    huey = MemoryHuey(immediate=True)
    registry = HandlerRegistry()
    registry.register(SendEmail, lambda cmd: f"sent to {cmd.recipient}")

    audit_log = []

    def audit_middleware(instance, next_call):
        audit_log.append(f"audit: {instance.recipient}")
        return next_call(instance)

    bus = HueyCommandBus(
        huey=huey, handler_registry=registry, middleware=[audit_middleware]
    )
    task = bus.dispatch(SendEmail(recipient="user@example.com"))

    assert task is not None
    assert task() == "sent to user@example.com"
    assert audit_log == ["audit: user@example.com"]


def test_huey_command_bus_missing_dependency():
    registry = HandlerRegistry()
    huey = MemoryHuey()
    with (
        patch("importlib.util.find_spec", return_value=None),
        pytest.raises(MissingDependencyError, match="huey is required"),
    ):
        HueyCommandBus(huey=huey, handler_registry=registry)


def test_native_async_command_bus_default_executor():
    registry = HandlerRegistry()
    registry.register(SendEmail, lambda cmd: f"sent to {cmd.recipient}")

    bus = NativeAsyncCommandBus(handler_registry=registry)
    future = bus.dispatch(SendEmail(recipient="default_async@example.com"))
    result = future.result(timeout=2.0)
    assert result == "sent to default_async@example.com"
    bus._executor.shutdown(wait=True)


def test_native_async_command_bus_with_middleware():
    registry = HandlerRegistry()
    registry.register(SendEmail, lambda cmd: f"sent to {cmd.recipient}")

    log = []

    def mw(instance, next_call):
        log.append("mw_called")
        return next_call(instance)

    executor = ThreadPoolExecutor(max_workers=2)
    bus = NativeAsyncCommandBus(
        handler_registry=registry, middleware=[mw], executor=executor
    )

    future = bus.dispatch(SendEmail(recipient="async@example.com"))
    result = future.result(timeout=2.0)

    assert result == "sent to async@example.com"
    assert log == ["mw_called"]
    executor.shutdown(wait=True)
