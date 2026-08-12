from collections.abc import Callable

import pytest
from hexastack_core.domain import Generic, Query
from hexastack_cqrs.adapters.buses.query.synchronous import (
    SynchronousQueryBus,
)
from hexastack_cqrs.infra.registries.handler import (
    HandlerRegistry,
    HandlerRegistryError,
)


class GetUserProfile(Query[dict[str, str]]):
    user_id: str


class QueryTrackingMiddleware:
    def __init__(self) -> None:
        self.called = False

    def __call__[G: Generic, R](self, instance: G, next_call: Callable[[G], R]) -> R:
        self.called = True
        return next_call(instance)


def test_synchronous_query_bus_dispatch():
    registry = HandlerRegistry()
    registry.register(GetUserProfile, lambda q: {"id": q.user_id, "name": "Alice"})

    bus = SynchronousQueryBus(handler_registry=registry)
    result = bus.dispatch(GetUserProfile(user_id="u-1"))

    assert result == {"id": "u-1", "name": "Alice"}


def test_synchronous_query_bus_with_middleware():
    registry = HandlerRegistry()
    registry.register(GetUserProfile, lambda q: {"id": q.user_id, "name": "Bob"})

    mw = QueryTrackingMiddleware()
    bus = SynchronousQueryBus(handler_registry=registry, middleware=[mw])

    result = bus.dispatch(GetUserProfile(user_id="u-2"))
    assert result == {"id": "u-2", "name": "Bob"}
    assert mw.called is True


def test_synchronous_query_bus_unregistered_raises():
    registry = HandlerRegistry()
    bus = SynchronousQueryBus(handler_registry=registry)

    with pytest.raises(HandlerRegistryError):
        bus.dispatch(GetUserProfile(user_id="u-unknown"))
