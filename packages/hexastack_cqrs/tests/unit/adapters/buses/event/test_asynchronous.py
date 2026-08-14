from concurrent.futures import ThreadPoolExecutor
from unittest.mock import patch

import pytest
from huey import MemoryHuey

from hexastack_core.domain import Event
from hexastack_core.domain.exceptions import MissingDependencyError
from hexastack_cqrs.adapters.buses.event.asynchronous import (
    HueyEventBus,
    NativeAsyncEventBus,
)


class OrderCreated(Event):
    order_id: str


def test_huey_event_bus_with_middleware_and_clear():
    huey = MemoryHuey(immediate=True)
    mw_log = []

    def mw(instance, next_call):
        mw_log.append(f"mw:{instance.order_id}")
        return next_call(instance)

    bus = HueyEventBus(huey=huey, middleware=[mw])
    received: list[str] = []

    bus.subscribe(OrderCreated, lambda evt: received.append(evt.order_id))
    tasks = bus.publish(OrderCreated(order_id="ord-123"))

    assert len(tasks) == 1
    assert tasks[0]() is None
    assert received == ["ord-123"]
    assert mw_log == ["mw:ord-123"]

    # Clear
    bus.clear()
    assert len(bus.handlers(OrderCreated)) == 0


def test_huey_event_bus_missing_dependency():
    huey = MemoryHuey()
    with (
        patch("importlib.util.find_spec", return_value=None),
        pytest.raises(MissingDependencyError, match="huey is required"),
    ):
        HueyEventBus(huey=huey)


def test_native_async_event_bus_default_executor_and_clear():
    bus = NativeAsyncEventBus()
    received: list[str] = []

    bus.subscribe(OrderCreated, lambda evt: received.append(evt.order_id))
    futures = bus.publish(OrderCreated(order_id="ord-456"))

    assert len(futures) == 1
    futures[0].result(timeout=2.0)
    assert received == ["ord-456"]

    bus.clear()
    assert len(bus.handlers(OrderCreated)) == 0
    bus._executor.shutdown(wait=True)


def test_native_async_event_bus_with_middleware():
    executor = ThreadPoolExecutor(max_workers=2)
    mw_log = []

    def mw(instance, next_call):
        mw_log.append("async_mw")
        return next_call(instance)

    bus = NativeAsyncEventBus(middleware=[mw], executor=executor)
    received: list[str] = []

    bus.subscribe(OrderCreated, lambda evt: received.append(evt.order_id))
    futures = bus.publish(OrderCreated(order_id="ord-789"))

    assert len(futures) == 1
    futures[0].result(timeout=2.0)
    assert received == ["ord-789"]
    assert mw_log == ["async_mw"]

    executor.shutdown(wait=True)
