from dataclasses import dataclass

import pytest

from hexastack_core.domain import Event
from hexastack_cqrs.adapters.buses.event.recording import RecordingEventBus


@dataclass(frozen=True)
class UserCreatedEvent(Event):
    user_id: str


@dataclass(frozen=True)
class OrderPlacedEvent(Event):
    order_id: str


@dataclass(frozen=True)
class PaymentReceivedEvent(Event):
    pass


def test_recording_event_bus_journal_and_assertions():
    bus = RecordingEventBus()
    dispatched_events: list[Event] = []

    bus.subscribe(UserCreatedEvent, lambda e: dispatched_events.append(e))

    e1 = UserCreatedEvent(user_id="u-1")
    e2 = OrderPlacedEvent(order_id="o-100")
    e3 = UserCreatedEvent(user_id="u-2")

    bus.publish(e1)
    bus.publish(e2)
    bus.publish(e3)

    # Verify handler execution
    assert dispatched_events == [e1, e3]

    # Verify journal tracking
    assert bus.published_events == [e1, e2, e3]
    assert bus.has_published(UserCreatedEvent) is True
    assert bus.has_published(OrderPlacedEvent) is True
    assert bus.has_published(PaymentReceivedEvent) is False

    # Test get_published
    user_events = bus.get_published(UserCreatedEvent)
    assert user_events == [e1, e3]

    # Test assert_published with and without count
    bus.assert_published(UserCreatedEvent)
    bus.assert_published(UserCreatedEvent, count=2)
    bus.assert_published(OrderPlacedEvent, count=1)

    # Test failure case
    with pytest.raises(
        AssertionError, match="Expected event of type PaymentReceivedEvent"
    ):
        bus.assert_published(PaymentReceivedEvent)

    with pytest.raises(
        AssertionError,
        match="Expected 3 event\\(s\\) of type UserCreatedEvent, but found 2",
    ):
        bus.assert_published(UserCreatedEvent, count=3)


def test_recording_event_bus_clearing():
    bus = RecordingEventBus()
    received: list[Event] = []
    bus.subscribe(UserCreatedEvent, lambda e: received.append(e))

    bus.publish(UserCreatedEvent(user_id="u-10"))
    assert len(bus.published_events) == 1
    assert len(received) == 1

    # clear_recorded removes journal entries but keeps subscription
    bus.clear_recorded()
    assert len(bus.published_events) == 0

    bus.publish(UserCreatedEvent(user_id="u-20"))
    assert len(bus.published_events) == 1
    assert len(received) == 2

    # clear removes both journal and subscription
    bus.clear()
    assert len(bus.published_events) == 0
    bus.publish(UserCreatedEvent(user_id="u-30"))
    assert len(bus.published_events) == 1
    assert len(received) == 2  # not dispatched to handler
