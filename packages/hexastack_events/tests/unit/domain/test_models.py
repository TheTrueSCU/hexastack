from datetime import UTC, datetime

from hexastack_events.domain.models import (
    CloudEventEnvelope,
    OutboxRecord,
    OutboxStatus,
)


def test_outbox_status_enum_values():
    assert OutboxStatus.PENDING == "PENDING"
    assert OutboxStatus.PUBLISHED == "PUBLISHED"
    assert OutboxStatus.FAILED == "FAILED"
    assert isinstance(OutboxStatus.PENDING, str)
    assert isinstance(OutboxStatus.PUBLISHED, str)
    assert isinstance(OutboxStatus.FAILED, str)


def test_outbox_record_defaults_and_lifecycle():
    rec = OutboxRecord(
        id="rec-1",
        event_type="UserCreatedEvent",
        payload={"user_id": "u1", "email": "test@example.com"},
    )
    # Default fields
    assert rec.source == "hexastack"
    assert rec.status == OutboxStatus.PENDING
    assert rec.retry_count == 0
    assert rec.correlation_id is None
    assert rec.tenant_id is None
    assert rec.published_at is None
    assert rec.last_error is None
    assert isinstance(rec.created_at, datetime)
    assert rec.created_at.tzinfo == UTC

    # First failure
    rec.mark_failed("Broker connection refused")
    assert rec.status == OutboxStatus.FAILED
    assert rec.retry_count == 1
    assert rec.last_error == "Broker connection refused"

    # Second failure
    rec.mark_failed("Broker timeout retry 2")
    assert rec.status == OutboxStatus.FAILED
    assert rec.retry_count == 2
    assert rec.last_error == "Broker timeout retry 2"

    # Published
    rec.mark_published()
    assert rec.status == OutboxStatus.PUBLISHED
    assert rec.published_at is not None
    assert rec.last_error is None
    assert rec.retry_count == 2  # retry_count preserved for auditing


def test_cloudevent_envelope_defaults():
    env = CloudEventEnvelope(
        id="ce-default",
        source="services/order",
        type="order.placed",
        time="2026-08-14T10:00:00Z",
        data={"order_id": "o-1"},
    )
    assert env.specversion == "1.0"
    assert env.datacontenttype == "application/json"
    assert env.correlationid is None
    assert env.tenantid is None
    assert env.id == "ce-default"
    assert env.source == "services/order"
    assert env.type == "order.placed"
    assert env.time == "2026-08-14T10:00:00Z"
    assert env.data == {"order_id": "o-1"}
