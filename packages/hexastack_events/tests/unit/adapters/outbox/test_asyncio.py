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


def test_asyncio_outbox_relay_defaults():
    storage = InMemoryOutboxStorage()
    bus = InMemoryDistributedEventBus()

    relay = AsyncioOutboxRelay(storage=storage, bus=bus)
    assert relay._poll_interval == 1.0
    assert relay._batch_size == 50
    assert relay._running is False

    # Stop when not running is a no-op
    relay.stop()
    assert relay._running is False


def test_asyncio_outbox_relay_batch_distributed_and_standard_bus():
    storage = InMemoryOutboxStorage()
    dist_bus = InMemoryDistributedEventBus()

    rec1 = OutboxRecord(
        id="rec-async-1",
        event_type="OrderShippedEvent",
        source="shipping-service",
        payload={"order_id": "ord-100", "tracking": "TRK999"},
        correlation_id="corr-ship-1",
        tenant_id="tenant-1",
    )
    storage.save(rec1)

    relay = AsyncioOutboxRelay(
        storage=storage,
        bus=dist_bus,
        poll_interval_seconds=0.05,
        batch_size=10,
    )

    count = relay.publish_pending_batch(limit=10)
    assert count == 1
    assert len(dist_bus.published_envelopes) == 1
    assert dist_bus.published_envelopes[0].type == "OrderShippedEvent"
    assert dist_bus.published_envelopes[0].data["tracking"] == "TRK999"
    assert dist_bus.published_envelopes[0].correlationid == "corr-ship-1"
    assert dist_bus.published_envelopes[0].tenantid == "tenant-1"
    assert dist_bus.published_envelopes[0].datacontenttype == "application/json"

    # Record should now be marked PUBLISHED
    records = storage.get_all()
    assert records[0].status == OutboxStatus.PUBLISHED

    # Test with standard EventBusPort (non-distributed)
    mock_std_bus = MagicMock(spec=EventBusPort)
    rec2 = OutboxRecord(
        id="rec-async-2",
        event_type="InventoryDeductedEvent",
        payload={"sku": "SKU-1"},
    )
    storage.save(rec2)
    std_relay = AsyncioOutboxRelay(storage=storage, bus=mock_std_bus)
    count2 = std_relay.publish_pending_batch(limit=10)
    assert count2 == 1
    assert mock_std_bus.publish.called


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

    failed_recs = [r for r in storage.get_all() if r.id == "rec-fail-1"]
    assert len(failed_recs) == 1
    failed_rec = failed_recs[0]
    assert failed_rec.status == OutboxStatus.FAILED
    assert failed_rec.retry_count == 1
    assert "Broker connection timeout" in str(failed_rec.last_error)


@pytest.mark.anyio
async def test_asyncio_outbox_relay_start_stop_lifecycle():
    storage = InMemoryOutboxStorage()
    bus = InMemoryDistributedEventBus()

    rec = OutboxRecord(
        id="rec-loop-1",
        event_type="PingEvent",
        payload={"ping": True},
    )
    storage.save(rec)

    relay = AsyncioOutboxRelay(
        storage=storage,
        bus=bus,
        poll_interval_seconds=0.01,
        batch_size=5,
    )

    relay.start()
    assert relay._running is True

    # Idempotent start
    relay.start()
    assert relay._running is True

    # Wait for at least one poll loop iteration
    await anyio.sleep(0.05)

    assert len(bus.published_envelopes) >= 1

    relay.stop()
    assert relay._running is False
