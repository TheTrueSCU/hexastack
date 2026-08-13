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

        reconstructed = from_cloudevent(ce, InvoicePaidEvent)
        assert reconstructed == event

        envelope = to_envelope(event, source="https://hexastack.io/billing")
        assert envelope.source == "https://hexastack.io/billing"
        assert envelope.data["invoice_id"] == "inv-888"


def test_cloudevent_deserialization_error():
    with pytest.raises(EventSerializationError):
        from_cloudevent("invalid json", InvoicePaidEvent)
