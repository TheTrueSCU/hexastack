from hexastack_events.adapters.buses.in_memory import (
    InMemoryDistributedEventBus,
)
from hexastack_events.adapters.outbox.huey import HueyOutboxRelay
from hexastack_events.adapters.outbox.in_memory import InMemoryOutboxStorage
from hexastack_events.domain.models import OutboxRecord, OutboxStatus


def test_huey_outbox_relay_batch():
    storage = InMemoryOutboxStorage()
    bus = InMemoryDistributedEventBus()

    rec = OutboxRecord(
        id="rec-huey-1",
        event_type="RefundIssuedEvent",
        source="billing-service",
        payload={"refund_id": "ref-555", "amount": 49.99},
    )
    storage.save(rec)

    relay = HueyOutboxRelay(
        storage=storage,
        bus=bus,
        batch_size=10,
    )
    relay.start()

    count = relay.publish_pending_batch(limit=10)
    assert count == 1
    assert len(bus.published_envelopes) == 1
    assert bus.published_envelopes[0].type == "RefundIssuedEvent"
    assert bus.published_envelopes[0].data["amount"] == 49.99

    records = storage.get_all()
    assert records[0].status == OutboxStatus.PUBLISHED
    relay.stop()
