from hexastack_events.domain.context import EventContext


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
