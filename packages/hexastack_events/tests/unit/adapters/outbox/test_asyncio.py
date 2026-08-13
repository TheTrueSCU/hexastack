from unittest.mock import MagicMock

import anyio
import pytest
from hexastack_cqrs.ports.buses import EventBusPort
from hexastack_events.adapters.buses.in_memory import (
    InMemoryDistributedEventBus,
)
from hexastack_events.adapters.outbox.asyncio import AsyncioOutboxRelay
from hexastack_events.adapters.outbox.in_memory import InMemoryOutboxStorage
from hexastack_events.domain.models import OutboxRecord, OutboxStatus


def test_asyncio_outbox_relay_batch():
    storage = InMemoryOutboxStorage()
    bus = InMemoryDistributedEventBus()

    rec = OutboxRecord(
        id="rec-async-1",
        event_type="OrderShippedEvent",
        source="shipping-service",
        payload={"order_id": "ord-100", "tracking": "TRK999"},
        correlation_id="corr-ship-1",
    )
    storage.save(rec)

    relay = AsyncioOutboxRelay(
        storage=storage,
        bus=bus,
        poll_interval_seconds=0.1,
        batch_size=10,
    )

    count = relay.publish_pending_batch(limit=10)
    assert count == 1
    assert len(bus.published_envelopes) == 1
    assert bus.published_envelopes[0].type == "OrderShippedEvent"
    assert bus.published_envelopes[0].data["tracking"] == "TRK999"

    # Record should now be marked PUBLISHED
    records = storage.get_all()
    assert records[0].status == OutboxStatus.PUBLISHED


def test_asyncio_outbox_relay_failure_handling():
    storage = InMemoryOutboxStorage()
    mock_bus = MagicMock(spec=InMemoryDistributedEventBus)
    mock_bus.publish_envelope.side_effect = RuntimeError("Broker connection timeout")

    rec = OutboxRecord(
        id="rec-fail-1",
        event_type="PaymentFailedEvent",
        source="billing",
        payload={"amount": 50},
    )
    storage.save(rec)

    relay = AsyncioOutboxRelay(storage=storage, bus=mock_bus)
    count = relay.publish_pending_batch(limit=10)
    assert count == 0

    records = [r for r in storage.get_all() if r.id == "rec-fail-1"]
    assert len(records) == 1
    assert records[0].status == OutboxStatus.FAILED
    assert "Broker connection timeout" in (records[0].last_error or "")


def test_asyncio_outbox_relay_standard_event_bus():
    storage = InMemoryOutboxStorage()
    mock_bus = MagicMock(spec=EventBusPort)

    rec = OutboxRecord(
        id="rec-std-1",
        event_type="ItemAddedEvent",
        source="inventory",
        payload={"item": "book"},
    )
    storage.save(rec)

    relay = AsyncioOutboxRelay(storage=storage, bus=mock_bus)
    count = relay.publish_pending_batch(limit=10)
    assert count == 1
    assert mock_bus.publish.called


@pytest.mark.anyio
async def test_asyncio_outbox_relay_start_stop():
    storage = InMemoryOutboxStorage()
    bus = InMemoryDistributedEventBus()

    rec = OutboxRecord(
        id="rec-loop-1",
        event_type="UserRegisteredEvent",
        source="auth",
        payload={"email": "alice@example.com"},
    )
    storage.save(rec)

    relay = AsyncioOutboxRelay(storage=storage, bus=bus, poll_interval_seconds=0.05)
    relay.start()
    assert relay._running is True
    assert relay._task is not None

    # Let the poll loop run for a brief moment
    await anyio.sleep(0.1)

    relay.stop()
    assert relay._running is False
    assert relay._task is None

    # Record should have been picked up and published
    records = [r for r in storage.get_all() if r.id == "rec-loop-1"]
    assert len(records) == 1
    assert records[0].status == OutboxStatus.PUBLISHED
