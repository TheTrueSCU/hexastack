from datetime import UTC, datetime

import pytest
from hexastack_core.domain import Event
from hexastack_core.utils.context import (
    UserContext,
    correlation_scope,
    set_user_context,
)
from hexastack_events.adapters.cloudevents.serializer import (
    cloudevent_to_dict,
    cloudevent_to_json,
    from_cloudevent,
    to_cloudevent,
    to_envelope,
)
from hexastack_events.domain.exceptions import EventSerializationError


class InvoicePaidEvent(Event):
    invoice_id: str
    amount: float
    currency: str = "USD"


def test_cloudevent_serializer_defaults():
    event = InvoicePaidEvent(invoice_id="inv-default", amount=100.0)
    fixed_time = datetime(2026, 8, 14, 12, 0, 0, tzinfo=UTC)

    # Defaults check (no context, no custom source/id/type)
    ce = to_cloudevent(
        event,
        event_id="fixed-event-id",
        time=fixed_time,
        extensions={"custom_ext": "value_123"},
    )
    assert ce["id"] == "fixed-event-id"
    assert ce["source"] == "hexastack"
    assert ce["type"] == "InvoicePaidEvent"
    assert ce["specversion"] == "1.0"
    assert ce["datacontenttype"] == "application/json"
    assert ce["time"] == "2026-08-14T12:00:00+00:00"
    assert ce["custom_ext"] == "value_123"
    assert "correlationid" not in ce.get_attributes()
    assert "tenantid" not in ce.get_attributes()

    # to_envelope defaults
    envelope = to_envelope(event)
    assert envelope.source == "hexastack"
    assert envelope.type == "InvoicePaidEvent"
    assert envelope.specversion == "1.0"
    assert envelope.datacontenttype == "application/json"
    assert envelope.data["invoice_id"] == "inv-default"


def test_cloudevent_serializer_roundtrip():
    event = InvoicePaidEvent(invoice_id="inv-888", amount=2500.0)

    with correlation_scope("corr-invoice-1"):
        set_user_context(UserContext(user_id="usr_1", tenant_id="tenant_corp"))
        ce = to_cloudevent(
            event,
            source="https://hexastack.io/billing",
            event_type="io.hexastack.billing.invoice_paid",
        )

        assert ce["id"] is not None
        assert ce["source"] == "https://hexastack.io/billing"
        assert ce["type"] == "io.hexastack.billing.invoice_paid"
        assert ce["correlationid"] == "corr-invoice-1"
        assert ce["tenantid"] == "tenant_corp"

        ce_dict = cloudevent_to_dict(ce)
        assert ce_dict["data"]["invoice_id"] == "inv-888"

        ce_json = cloudevent_to_json(ce)
        assert "inv-888" in ce_json

        # Reconstruct from CloudEvent instance
        reconstructed = from_cloudevent(ce, InvoicePaidEvent)
        assert reconstructed == event

        # Reconstruct from JSON string
        reconstructed_from_json = from_cloudevent(ce_json, InvoicePaidEvent)
        assert reconstructed_from_json == event

        # Reconstruct from dict
        reconstructed_from_dict = from_cloudevent(ce_dict, InvoicePaidEvent)
        assert reconstructed_from_dict == event

        envelope = to_envelope(event, source="https://hexastack.io/billing")
        assert envelope.source == "https://hexastack.io/billing"
        assert envelope.correlationid == "corr-invoice-1"
        assert envelope.tenantid == "tenant_corp"
        assert envelope.data["invoice_id"] == "inv-888"


def test_cloudevent_deserialization_error():
    with pytest.raises(
        EventSerializationError,
        match="Failed to deserialize CloudEvent into 'InvoicePaidEvent'",
    ):
        from_cloudevent("invalid json content", InvoicePaidEvent)
