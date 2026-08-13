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

    # Test get_published
    user_events = bus.get_published(UserCreatedEvent)
    assert user_events == [e1, e3]

    # Test assert_published
    bus.assert_published(UserCreatedEvent, count=2)
    bus.assert_published(OrderPlacedEvent, count=1)

    # Test failure case
    @dataclass(frozen=True)
    class PaymentReceivedEvent(Event):
        pass

    with pytest.raises(
        AssertionError, match="Expected event of type PaymentReceivedEvent"
    ):
        bus.assert_published(PaymentReceivedEvent)

    with pytest.raises(
        AssertionError,
        match="Expected 3 event\\(s\\) of type UserCreatedEvent, but found 2",
    ):
        bus.assert_published(UserCreatedEvent, count=3)

    # Clear recorded
    bus.clear_recorded()
    assert len(bus.published_events) == 0
    assert len(bus.handlers(UserCreatedEvent)) == 1

    # Full clear
    bus.clear()
    assert len(bus.handlers(UserCreatedEvent)) == 0
