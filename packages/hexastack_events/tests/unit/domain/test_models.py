from hexastack_events.domain.models import (
    CloudEventEnvelope,
    OutboxRecord,
    OutboxStatus,
)


def test_outbox_record_lifecycle():
    rec = OutboxRecord(
        id="rec-1",
        event_type="UserCreatedEvent",
        source="auth-service",
        payload={"user_id": "u1", "email": "test@example.com"},
        correlation_id="corr-100",
        tenant_id="tenant-1",
    )
    assert rec.status == OutboxStatus.PENDING
    assert rec.retry_count == 0
    assert rec.published_at is None

    rec.mark_failed("Broker timeout")
    assert rec.status == OutboxStatus.FAILED
    assert rec.retry_count == 1
    assert rec.last_error == "Broker timeout"

    rec.mark_published()
    assert rec.status == OutboxStatus.PUBLISHED
    assert rec.published_at is not None
    assert rec.last_error is None


def test_cloudevent_envelope():
    env = CloudEventEnvelope(
        id="ce-1",
        source="services/payments",
        type="io.hexastack.payment.received",
        time="2026-08-13T08:00:00Z",
        correlationid="corr-99",
        tenantid="tenant-gold",
        data={"payment_id": "pay-100", "amount": 250.0},
    )
    assert env.specversion == "1.0"
    assert env.id == "ce-1"
    assert env.data["amount"] == 250.0
