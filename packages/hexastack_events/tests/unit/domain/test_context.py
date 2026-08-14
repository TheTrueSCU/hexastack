from datetime import UTC, datetime

from hexastack_events.domain.context import EventContext


def test_event_context_defaults():
    ctx = EventContext(
        event_id="evt-default",
        event_type="UserCreated",
        source="users",
    )
    assert ctx.event_id == "evt-default"
    assert ctx.event_type == "UserCreated"
    assert ctx.source == "users"
    assert ctx.datacontenttype == "application/json"
    assert ctx.correlation_id is None
    assert ctx.tenant_id is None
    assert ctx.extensions == {}
    assert isinstance(ctx.time, datetime)
    assert ctx.time.tzinfo == UTC


def test_event_context_fields():
    ctx = EventContext(
        event_id="evt-123",
        event_type="OrderPlacedEvent",
        source="https://hexastack.io/orders",
        correlation_id="corr-abc",
        tenant_id="tenant-42",
        extensions={"partition_key": "user_99"},
    )
    assert ctx.event_id == "evt-123"
    assert ctx.event_type == "OrderPlacedEvent"
    assert ctx.source == "https://hexastack.io/orders"
    assert ctx.correlation_id == "corr-abc"
    assert ctx.tenant_id == "tenant-42"
    assert ctx.extensions["partition_key"] == "user_99"
