import json
from datetime import UTC, datetime

import pytest
from inline_snapshot import snapshot

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

_FIXED_TIME = datetime(2026, 8, 14, 12, 0, 0, tzinfo=UTC)
_FIXED_ID = "fixed-event-id"


class InvoicePaidEvent(Event):
    invoice_id: str
    amount: float
    currency: str = "USD"


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


@pytest.mark.snapshot
def test_cloudevent_serializer_defaults():
    correlation_id_ctx.set("")
    set_user_context(None)

    event = InvoicePaidEvent(invoice_id="inv-default", amount=100.0)
    ce = to_cloudevent(
        event,
        event_id=_FIXED_ID,
        time=_FIXED_TIME,
        extensions={"custom_ext": "value_123"},
    )

    assert cloudevent_to_dict(ce) == snapshot(
        {
            "id": "fixed-event-id",
            "source": "hexastack",
            "type": "InvoicePaidEvent",
            "specversion": "1.0",
            "time": "2026-08-14T12:00:00+00:00",
            "datacontenttype": "application/json",
            "custom_ext": "value_123",
            "data": {"invoice_id": "inv-default", "amount": 100.0, "currency": "USD"},
        }
    )


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

        # Deserialize where ce.data is string-encoded JSON
        ce_with_str_data = dict(d)
        ce_with_str_data["data"] = json.dumps(d["data"])
        restored_from_str_payload = from_cloudevent(ce_with_str_data, InvoicePaidEvent)
        assert restored_from_str_payload.invoice_id == "inv-888"


@pytest.mark.snapshot
def test_cloudevent_serializer_with_context():
    event = InvoicePaidEvent(invoice_id="inv-888", amount=2500.0)

    with correlation_scope("corr-invoice-1"):
        set_user_context(UserContext(user_id="usr_1", tenant_id="tenant_corp"))
        ce = to_cloudevent(
            event,
            event_id=_FIXED_ID,
            time=_FIXED_TIME,
            source="https://hexastack.io/billing",
            event_type="io.hexastack.billing.invoice_paid",
        )

        assert cloudevent_to_dict(ce) == snapshot(
            {
                "id": "fixed-event-id",
                "source": "https://hexastack.io/billing",
                "type": "io.hexastack.billing.invoice_paid",
                "specversion": "1.0",
                "time": "2026-08-14T12:00:00+00:00",
                "datacontenttype": "application/json",
                "correlationid": "corr-invoice-1",
                "tenantid": "tenant_corp",
                "data": {"invoice_id": "inv-888", "amount": 2500.0, "currency": "USD"},
            }
        )


@pytest.mark.snapshot
def test_to_envelope_shape():
    correlation_id_ctx.set("")
    set_user_context(None)

    event = InvoicePaidEvent(invoice_id="inv-env-1", amount=75.0)
    envelope = to_envelope(
        event,
        source="custom-src",
        event_type="custom-type",
        event_id="custom-id",
    )

    assert envelope.id == "custom-id"
    assert envelope.source == "custom-src"
    assert envelope.type == "custom-type"
    assert envelope.datacontenttype == "application/json"
    assert envelope.correlationid is None
    assert envelope.tenantid is None
    assert isinstance(envelope.time, str)
    assert envelope.data == {
        "invoice_id": "inv-env-1",
        "amount": 75.0,
        "currency": "USD",
    }

    # Default to_envelope without explicit kwargs
    default_env = to_envelope(event)
    assert default_env.source == "hexastack"
    assert default_env.type == "InvoicePaidEvent"
    assert default_env.datacontenttype == "application/json"
    assert default_env.data == {
        "invoice_id": "inv-env-1",
        "amount": 75.0,
        "currency": "USD",
    }
