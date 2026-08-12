from concurrent.futures import ThreadPoolExecutor

from hexastack_core.domain import Event
from hexastack_cqrs.adapters.buses.event.asynchronous import (
    HueyEventBus,
    NativeAsyncEventBus,
)
from huey import MemoryHuey


class OrderCreated(Event):
    order_id: str


def test_huey_event_bus():
    huey = MemoryHuey(immediate=True)
    bus = HueyEventBus(huey=huey)
    received: list[str] = []

    bus.subscribe(OrderCreated, lambda evt: received.append(evt.order_id))
    tasks = bus.publish(OrderCreated(order_id="ord-123"))

    assert len(tasks) == 1
    assert tasks[0]() is None
    assert received == ["ord-123"]


def test_native_async_event_bus():
    executor = ThreadPoolExecutor(max_workers=2)
    bus = NativeAsyncEventBus(executor=executor)
    received: list[str] = []

    bus.subscribe(OrderCreated, lambda evt: received.append(evt.order_id))
    futures = bus.publish(OrderCreated(order_id="ord-456"))

    assert len(futures) == 1
    futures[0].result(timeout=2.0)
    assert received == ["ord-456"]

    executor.shutdown(wait=True)
