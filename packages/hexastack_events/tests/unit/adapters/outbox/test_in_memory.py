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
