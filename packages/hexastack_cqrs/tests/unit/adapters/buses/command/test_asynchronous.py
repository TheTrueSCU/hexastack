from concurrent.futures import ThreadPoolExecutor
from unittest.mock import patch

import pytest
from hexastack_core.domain import Command
from hexastack_core.domain.exceptions import MissingDependencyError
from hexastack_cqrs.adapters.buses.command.asynchronous import (
    HueyCommandBus,
    NativeAsyncCommandBus,
)
from hexastack_cqrs.infra.registries.handler import HandlerRegistry
from huey import MemoryHuey


class SendEmail(Command):
    recipient: str


def test_huey_command_bus():
    huey = MemoryHuey(immediate=True)
    registry = HandlerRegistry()
    registry.register(SendEmail, lambda cmd: f"sent to {cmd.recipient}")

    bus = HueyCommandBus(huey=huey, handler_registry=registry)
    task = bus.dispatch(SendEmail(recipient="user@example.com"))

    assert task is not None
    assert task() == "sent to user@example.com"


def test_huey_command_bus_missing_dependency():
    registry = HandlerRegistry()
    huey = MemoryHuey()
    with (
        patch("importlib.util.find_spec", return_value=None),
        pytest.raises(MissingDependencyError, match="huey is required"),
    ):
        HueyCommandBus(huey=huey, handler_registry=registry)


def test_native_async_command_bus():
    registry = HandlerRegistry()
    registry.register(SendEmail, lambda cmd: f"sent to {cmd.recipient}")

    executor = ThreadPoolExecutor(max_workers=2)
    bus = NativeAsyncCommandBus(handler_registry=registry, executor=executor)

    future = bus.dispatch(SendEmail(recipient="async@example.com"))
    result = future.result(timeout=2.0)

    assert result == "sent to async@example.com"
    executor.shutdown(wait=True)
