from hexastack_core.domain.exceptions import HexastackError
from hexastack_events.domain.exceptions import (
    DuplicateEventError,
    EventDeliveryError,
    EventError,
    EventSerializationError,
    OutboxError,
)


def test_events_exceptions_hierarchy():
    err = EventError("Base event error")
    assert isinstance(err, HexastackError)

    outbox_err = OutboxError("Storage write failed")
    assert isinstance(outbox_err, EventError)

    ser_err = EventSerializationError("Invalid payload")
    assert isinstance(ser_err, EventError)

    deliv_err = EventDeliveryError("Broker unreachable")
    assert isinstance(deliv_err, EventError)

    dup_err = DuplicateEventError("Event already processed")
    assert isinstance(dup_err, EventError)
