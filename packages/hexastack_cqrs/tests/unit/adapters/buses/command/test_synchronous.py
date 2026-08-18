from collections.abc import Callable

import pytest

from hexastack_core.domain import Command, Generic
from hexastack_cqrs.adapters.buses.command.synchronous import (
    SynchronousCommandBus,
)
from hexastack_cqrs.infra.registries.handler import (
    HandlerRegistry,
    HandlerRegistryError,
)


class CreateUser(Command):
    username: str


class UppercaseTrackingMiddleware:
    def __init__(self) -> None:
        self.called = False

    def __call__[G: Generic, R](self, instance: G, next_call: Callable[[G], R]) -> R:
        self.called = True
        return next_call(instance)


def test_synchronous_command_bus_dispatch():
    registry = HandlerRegistry()
    registry.register(CreateUser, lambda cmd: f"created {cmd.username}")

    bus = SynchronousCommandBus(handler_registry=registry)
    res = bus.dispatch(CreateUser(username="Alice"))

    assert res == "created Alice"


def test_synchronous_command_bus_unregistered_raises():
    registry = HandlerRegistry()
    bus = SynchronousCommandBus(handler_registry=registry)

    with pytest.raises(HandlerRegistryError):
        bus.dispatch(CreateUser(username="Nobody"))


def test_synchronous_command_bus_with_middleware():
    registry = HandlerRegistry()
    registry.register(CreateUser, lambda cmd: f"created {cmd.username}")

    mw = UppercaseTrackingMiddleware()
    bus = SynchronousCommandBus(handler_registry=registry, middleware=[mw])

    res = bus.dispatch(CreateUser(username="Bob"))
    assert res == "created Bob"
    assert mw.called is True
