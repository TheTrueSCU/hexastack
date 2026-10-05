from collections.abc import Callable

from hexastack_core.domain import Event, Generic
from hexastack_cqrs.adapters.buses.event.synchronous import SynchronousEventBus


class UserRegistered(Event):
    user_id: str


class OrderPlaced(Event):
    order_id: str


class TrackingMiddleware:
    def __init__(self) -> None:
        self.intercepted: list[str] = []

    def __call__[G: Generic, R](self, instance: G, next_call: Callable[[G], R]) -> R:
        self.intercepted.append(instance.__class__.__name__)
        return next_call(instance)


def test_synchronous_event_bus_clear():
    bus = SynchronousEventBus()
    handled: list[str] = []

    bus.subscribe(UserRegistered, lambda e: handled.append(e.user_id))
    bus.clear()
    bus.publish(UserRegistered(user_id="u-100"))

    assert handled == []


def test_synchronous_event_bus_publish():
    bus = SynchronousEventBus()
    received_1: list[str] = []
    received_2: list[str] = []

    bus.subscribe(UserRegistered, lambda e: received_1.append(e.user_id))
    bus.subscribe(UserRegistered, lambda e: received_2.append(f"welcome-{e.user_id}"))

    event = UserRegistered(user_id="u-100")
    bus.publish(event)

    assert received_1 == ["u-100"]
    assert received_2 == ["welcome-u-100"]


def test_synchronous_event_bus_with_middleware():
    mw = TrackingMiddleware()
    bus = SynchronousEventBus(middleware=[mw])
    handled: list[str] = []

    bus.subscribe(OrderPlaced, lambda e: handled.append(e.order_id))
    bus.publish(OrderPlaced(order_id="ord-99"))

    assert handled == ["ord-99"]
    assert mw.intercepted == ["OrderPlaced"]
