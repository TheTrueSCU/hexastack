from typing import Any

from hexastack_core.domain import Event
from hexastack_events.adapters.buses.in_memory import (
    InMemoryDistributedEventBus,
)
from hexastack_events.domain.models import CloudEventEnvelope


class ItemRestockedEvent(Event):
    item_id: str
    quantity: int


def test_in_memory_distributed_event_bus():
    bus = InMemoryDistributedEventBus()
    received: list[Any] = []

    bus.subscribe("ItemRestockedEvent", lambda evt: received.append(evt))

    event = ItemRestockedEvent(item_id="item-77", quantity=50)
    bus.publish(event)

    assert len(bus.published_events) == 1
    assert len(received) == 1
    assert received[0].item_id == "item-77"

    envelope = CloudEventEnvelope(
        id="ce-2",
        source="warehouse-svc",
        type="ItemRestockedEvent",
        time="2026-08-13T08:00:00Z",
        data={"item_id": "item-77", "quantity": 50},
    )
    bus.publish_envelope(envelope)
    assert len(bus.published_envelopes) == 1
    assert len(received) == 2
