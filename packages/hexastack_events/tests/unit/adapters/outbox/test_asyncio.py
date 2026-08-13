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
