from unittest.mock import MagicMock

from hexastack_cqrs.ports.buses import EventBusPort
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
        correlation_id="corr-ref-1",
        tenant_id="tenant-gold",
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
    assert bus.published_envelopes[0].correlationid == "corr-ref-1"
    assert bus.published_envelopes[0].tenantid == "tenant-gold"

    records = storage.get_all()
    assert records[0].status == OutboxStatus.PUBLISHED
    relay.stop()


def test_huey_outbox_relay_defaults_and_lifecycle():
    storage = InMemoryOutboxStorage()
    bus = InMemoryDistributedEventBus()

    relay = HueyOutboxRelay(storage=storage, bus=bus)
    assert relay._batch_size == 50
    assert relay._huey is None
    assert relay._is_active is False

    relay.start()
    assert relay._is_active is True

    relay.stop()
    assert relay._is_active is False


def test_huey_outbox_relay_standard_bus_and_error():
    storage = InMemoryOutboxStorage()
    std_bus = MagicMock(spec=EventBusPort)

    rec = OutboxRecord(
        id="rec-huey-std",
        event_type="StandardEvent",
        payload={"x": 1},
    )
    storage.save(rec)

    relay = HueyOutboxRelay(storage=storage, bus=std_bus)
    count = relay.publish_pending_batch(limit=5)
    assert count == 1
    assert std_bus.publish.called

    # Error handling
    err_bus = MagicMock(spec=InMemoryDistributedEventBus)
    err_bus.publish_envelope.side_effect = RuntimeError("Huey broker error")
    rec_err = OutboxRecord(
        id="rec-huey-err",
        event_type="ErrorEvent",
        payload={"err": True},
    )
    storage.save(rec_err)
    err_relay = HueyOutboxRelay(storage=storage, bus=err_bus)
    count_err = err_relay.publish_pending_batch(limit=5)
    assert count_err == 0
    failed_records = [r for r in storage.get_all() if r.id == "rec-huey-err"]
    assert len(failed_records) == 1
    failed_record = failed_records[0]
    assert failed_record.status == OutboxStatus.FAILED
    assert failed_record.retry_count == 1
    assert "Huey broker error" in str(failed_record.last_error)


def test_huey_outbox_relay_with_lock_concurrency():
    import tempfile
    from pathlib import Path

    from hexastack_core.adapters.lock.file import FileLockAdapter

    with tempfile.TemporaryDirectory() as tmpdir:
        lock_path = Path(tmpdir) / "huey_outbox.lock"
        relay_lock = FileLockAdapter(lock_path)
        peer_lock = FileLockAdapter(lock_path)

        storage = InMemoryOutboxStorage()
        bus = InMemoryDistributedEventBus()

        storage.save(
            OutboxRecord(
                id="rec-huey-lock-1",
                event_type="RefundLockedEvent",
                payload={"refund_id": "ref-999"},
            )
        )

        relay = HueyOutboxRelay(
            storage=storage,
            bus=bus,
            lock=relay_lock,
        )

        # 1. Publishes when lock available
        count = relay.publish_pending_batch(limit=10)
        assert count == 1
        assert relay_lock.locked() is False

        # 2. Skips when lock held by peer worker process
        storage.save(
            OutboxRecord(
                id="rec-huey-lock-2",
                event_type="RefundLockedEvent2",
                payload={"refund_id": "ref-1000"},
            )
        )
        peer_acq = peer_lock.acquire()
        assert peer_acq is True
        count_skipped = relay.publish_pending_batch(limit=10)
        assert count_skipped == 0
        peer_lock.release()
