from datetime import UTC, datetime

import pytest

from hexastack_core.domain import Event
from hexastack_core.utils.context import (
    UserContext,
    correlation_id_ctx,
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
    correlation_id_ctx.set("")
    set_user_context(None)

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

        # Roundtrip via to_dict
        d = cloudevent_to_dict(ce)
        assert d["id"] == ce["id"]
        assert d["source"] == "https://hexastack.io/billing"
        assert d["type"] == "io.hexastack.billing.invoice_paid"
        assert d["correlationid"] == "corr-invoice-1"
        assert d["tenantid"] == "tenant_corp"
        assert d["data"] == {
            "invoice_id": "inv-888",
            "amount": 2500.0,
            "currency": "USD",
        }

        # Roundtrip via to_json
        raw_json = cloudevent_to_json(ce)
        assert isinstance(raw_json, str)

        # Deserialize back to domain Event
        restored = from_cloudevent(ce, InvoicePaidEvent)
        assert isinstance(restored, InvoicePaidEvent)
        assert restored.invoice_id == "inv-888"
        assert restored.amount == 2500.0
        assert restored.currency == "USD"

        # Deserialize from JSON
        restored_from_json = from_cloudevent(raw_json, InvoicePaidEvent)
        assert restored_from_json.invoice_id == "inv-888"

        # Deserialize from dict
        restored_from_dict = from_cloudevent(d, InvoicePaidEvent)
        assert restored_from_dict.invoice_id == "inv-888"


def test_cloudevent_deserialization_failure():
    invalid_ce_data = {
        "id": "bad-ce",
        "source": "unknown",
        "type": "InvoicePaidEvent",
        "specversion": "1.0",
        "data": "not-a-valid-dict",
    }
    with pytest.raises(
        EventSerializationError,
        match="Failed to deserialize CloudEvent into 'InvoicePaidEvent'",
    ):
        from_cloudevent(invalid_ce_data, InvoicePaidEvent)
