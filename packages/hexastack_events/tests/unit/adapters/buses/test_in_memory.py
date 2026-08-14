from typing import Any

from hexastack_core.domain import Event
from hexastack_events.adapters.buses.in_memory import (
    InMemoryDistributedEventBus,
)
from hexastack_events.domain.models import CloudEventEnvelope


class ItemRestockedEvent(Event):
    item_id: str
    quantity: int


class OtherEvent(Event):
    info: str


def test_in_memory_distributed_event_bus():
    bus = InMemoryDistributedEventBus()
    received: list[Any] = []

    bus.subscribe("ItemRestockedEvent", lambda evt: received.append(evt))

    event = ItemRestockedEvent(item_id="item-77", quantity=50)
    bus.publish(event)

    assert len(bus.published_events) == 1
    assert len(received) == 1
    assert received[0].item_id == "item-77"

    # Publishing event without subscriber
    bus.publish(OtherEvent(info="no-sub"))
    assert len(bus.published_events) == 2
    assert len(received) == 1

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
    assert received[1].id == "ce-2"

    # Envelope without subscriber
    other_envelope = CloudEventEnvelope(
        id="ce-other",
        source="warehouse-svc",
        type="UnsubscribedType",
        time="2026-08-13T08:00:00Z",
        data={},
    )
    bus.publish_envelope(other_envelope)
    assert len(bus.published_envelopes) == 2
    assert len(received) == 2

    # Clear
    bus.clear()
    assert len(bus.published_events) == 0
    assert len(bus.published_envelopes) == 0
