from hexastack_events.adapters.outbox.in_memory import InMemoryOutboxStorage
from hexastack_events.domain.models import OutboxRecord, OutboxStatus


def test_in_memory_outbox_storage():
    storage = InMemoryOutboxStorage()
    rec1 = OutboxRecord(
        id="rec-1",
        event_type="OrderCreated",
        source="order-service",
        payload={"order_id": "o1"},
    )
    rec2 = OutboxRecord(
        id="rec-2",
        event_type="PaymentReceived",
        source="billing-service",
        payload={"pay_id": "p1"},
    )

    storage.save_all([rec1, rec2])
    pending = storage.fetch_pending(limit=10)
    assert len(pending) == 2

    storage.mark_published("rec-1")
    pending_after = storage.fetch_pending(limit=10)
    assert len(pending_after) == 1
    assert pending_after[0].id == "rec-2"

    storage.mark_failed("rec-2", "Network error")
    all_recs = storage.get_all()
    failed_rec = next(r for r in all_recs if r.id == "rec-2")
    assert failed_rec.status == OutboxStatus.FAILED
    assert failed_rec.retry_count == 1


def test_outbox_relay_crash_recovery_and_deduplication():
    """Verify outbox relay crash recovery, retry, and event deduplication invariants."""
    from hexastack_events.adapters.outbox.asyncio import AsyncioOutboxRelay
    from hexastack_events.domain.models import CloudEventEnvelope
    from hexastack_events.ports.buses import DistributedEventBusPort

    class TestCrashBus(DistributedEventBusPort):
        def __init__(self):
            self.delivered: list[CloudEventEnvelope] = []
            self.fail_on_id: str | None = None

        def publish_envelope(self, envelope: CloudEventEnvelope) -> None:
            if envelope.id == self.fail_on_id:
                raise RuntimeError(f"Simulated bus crash on {envelope.id}")
            self.delivered.append(envelope)

        def publish(self, event):
            pass

        def subscribe(self, event_type, handler):
            pass

    storage = InMemoryOutboxStorage()
    rec1 = OutboxRecord(id="evt-1", event_type="UserCreated", payload={"user": "Alice"})
    rec2 = OutboxRecord(id="evt-2", event_type="UserCreated", payload={"user": "Bob"})
    rec3 = OutboxRecord(
        id="evt-3", event_type="UserCreated", payload={"user": "Charlie"}
    )
    storage.save_all([rec1, rec2, rec3])

    bus = TestCrashBus()
    bus.fail_on_id = "evt-2"

    relay = AsyncioOutboxRelay(storage=storage, bus=bus, batch_size=10)

    # 1. First cycle: evt-1 succeeds, evt-2 crashes and marks failed, evt-3 succeeds
    count = relay.publish_pending_batch(limit=10)
    assert count == 2  # evt-1 and evt-3 published

    delivered_ids = [e.id for e in bus.delivered]
    assert delivered_ids == ["evt-1", "evt-3"]

    # evt-2 should be in FAILED status with retry_count 1
    pending = storage.fetch_pending(limit=10)
    assert len(pending) == 1
    assert pending[0].id == "evt-2"
    assert pending[0].status == OutboxStatus.FAILED
    assert pending[0].retry_count == 1

    # 2. Worker reboot / recovery: bus recovers from failure
    bus.fail_on_id = None
    recovered_count = relay.publish_pending_batch(limit=10)
    assert recovered_count == 1

    # Invariant: evt-2 was delivered with stable ID allowing consumer deduplication
    assert len(bus.delivered) == 3
    final_delivered_ids = [e.id for e in bus.delivered]
    assert final_delivered_ids == ["evt-1", "evt-3", "evt-2"]

    # Invariant: storage is completely drained
    final_pending = storage.fetch_pending(limit=10)
    assert len(final_pending) == 0


def test_outbox_relay_transient_db_disconnect():
    """Verify relay resilience against transient database storage disconnects."""
    from hexastack_events.adapters.outbox.asyncio import AsyncioOutboxRelay
    from hexastack_events.domain.models import CloudEventEnvelope
    from hexastack_events.ports.buses import DistributedEventBusPort

    class MockBus(DistributedEventBusPort):
        def __init__(self):
            self.delivered = []

        def publish_envelope(self, envelope: CloudEventEnvelope) -> None:
            self.delivered.append(envelope)

        def publish(self, event):
            pass

        def subscribe(self, event_type, handler):
            pass

    class FlakyStorage(InMemoryOutboxStorage):
        def __init__(self):
            super().__init__()
            self.disconnected = False

        def fetch_pending(self, limit: int = 50):
            if self.disconnected:
                raise ConnectionError("Database connection lost")
            return super().fetch_pending(limit=limit)

    storage = FlakyStorage()
    storage.save(
        OutboxRecord(id="evt-safe", event_type="OrderPaid", payload={"amount": 100})
    )

    bus = MockBus()
    relay = AsyncioOutboxRelay(storage=storage, bus=bus)

    # 1. Simulate database outage
    storage.disconnected = True
    import pytest

    with pytest.raises(ConnectionError, match="Database connection lost"):
        relay.publish_pending_batch()

    # 2. Invariant: zero events published while database is disconnected
    assert len(bus.delivered) == 0

    # 3. Simulate database reconnection
    storage.disconnected = False
    count = relay.publish_pending_batch()
    assert count == 1
    assert len(bus.delivered) == 1
    assert bus.delivered[0].id == "evt-safe"
    assert len(storage.fetch_pending()) == 0


def test_outbox_poison_pill_retry_budget_exhaustion():
    """Verify that poison pill events exhaust their retry budget (5 attempts) and unblock queue."""
    from hexastack_events.adapters.outbox.asyncio import AsyncioOutboxRelay
    from hexastack_events.domain.models import CloudEventEnvelope
    from hexastack_events.ports.buses import DistributedEventBusPort

    class PoisonBus(DistributedEventBusPort):
        def publish_envelope(self, envelope: CloudEventEnvelope) -> None:
            if envelope.id == "poison-pill":
                raise ValueError("Permanent unparseable schema error")

        def publish(self, event):
            pass

        def subscribe(self, event_type, handler):
            pass

    storage = InMemoryOutboxStorage()
    poison_record = OutboxRecord(id="poison-pill", event_type="BrokenEvent", payload={})
    healthy_record = OutboxRecord(
        id="healthy-event", event_type="ValidEvent", payload={}
    )
    storage.save_all([poison_record, healthy_record])

    bus = PoisonBus()
    relay = AsyncioOutboxRelay(storage=storage, bus=bus, batch_size=10)

    # Run relay 5 times: healthy succeeds on round 1, poison fails 5 times
    for attempt in range(1, 6):
        relay.publish_pending_batch(limit=10)
        recs = storage.get_all()
        p = next(r for r in recs if r.id == "poison-pill")
        assert p.retry_count == attempt
        assert p.status == OutboxStatus.FAILED

    # On round 6, poison pill is permanently excluded from fetch_pending
    pending = storage.fetch_pending(limit=10)
    assert len(pending) == 0  # Poison pill is filtered out, queue is unblocked!
