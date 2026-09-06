from typing import Any

import pytest

from hexastack_core.domain import Command, Event, Query
from hexastack_cqrs.ports.buses import (
    CommandBusPort,
    EventBusPort,
    HandlerDispatcherPort,
    MiddlewarePort,
    QueryBusPort,
)


class SampleCommand(Command):
    name: str


class SampleEvent(Event):
    event_name: str


class SampleQuery(Query[str]):
    query_param: str


class MockCommandBus(CommandBusPort):
    def dispatch(self, command: Command) -> Any:
        return f"dispatched {command.__class__.__name__}"


class MockEventBus(EventBusPort):
    def __init__(self) -> None:
        self.published: list[Event] = []

    def publish(self, event: Event) -> None:
        self.published.append(event)


class MockQueryBus(QueryBusPort):
    def dispatch(self, query: Query[Any]) -> Any:
        return f"result of {query.__class__.__name__}"


def test_bus_ports():
    cmd_bus = MockCommandBus()
    assert cmd_bus.dispatch(SampleCommand(name="test")) == "dispatched SampleCommand"

    evt_bus = MockEventBus()
    event = SampleEvent(event_name="created")
    evt_bus.publish(event)
    assert evt_bus.published == [event]

    query_bus = MockQueryBus()
    assert query_bus.dispatch(SampleQuery(query_param="q")) == "result of SampleQuery"


def test_abstract_bus_ports_cannot_be_instantiated_directly():

    with pytest.raises(TypeError, match="Can't instantiate abstract class"):
        CommandBusPort()  # type: ignore[abstract]

    with pytest.raises(TypeError, match="Can't instantiate abstract class"):
        EventBusPort()  # type: ignore[abstract]

    with pytest.raises(TypeError, match="Can't instantiate abstract class"):
        QueryBusPort()  # type: ignore[abstract]

    with pytest.raises(TypeError, match="Can't instantiate abstract class"):
        HandlerDispatcherPort()  # type: ignore[abstract]

    # Test MiddlewarePort runtime_checkable protocol
    class CallableMiddleware:
        def __call__(self, instance, next_call):
            return next_call(instance)

    assert isinstance(CallableMiddleware(), MiddlewarePort)
    assert not isinstance(object(), MiddlewarePort)
