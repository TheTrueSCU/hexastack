from hexastack_core.domain.event import Event
from hexastack_core.domain.generic import Generic


class ItemCreatedEvent(Event):
    item_id: str


def test_event_inheritance_and_properties():
    event = ItemCreatedEvent(item_id="item-123")
    assert isinstance(event, Event)
    assert isinstance(event, Generic)
    assert event.item_id == "item-123"
