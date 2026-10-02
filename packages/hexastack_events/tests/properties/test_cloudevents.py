from hypothesis import given
from hypothesis import strategies as st

from hexastack_core.domain import Event
from hexastack_core.utils.context import (
    UserContext,
    correlation_id_ctx,
    set_correlation_id,
    set_user_context,
    user_ctx,
)
from hexastack_events.adapters.cloudevents import (
    cloudevent_to_dict,
    cloudevent_to_json,
    from_cloudevent,
    to_cloudevent,
    to_envelope,
)
from hexastack_events.domain.models import CloudEventEnvelope


class FuzzOrderEvent(Event):
    order_id: str
    user_id: str
    amount: float
    is_active: bool = True
    tags: list[str] = []


@given(
    order_id=st.text(min_size=1, max_size=50),
    user_id=st.text(min_size=1, max_size=50),
    amount=st.floats(min_value=0.0, max_value=1_000_000.0, allow_nan=False),
    is_active=st.booleans(),
    tags=st.lists(st.text(min_size=1, max_size=20), max_size=5),
    correlation_id=st.one_of(st.none(), st.uuids().map(str)),
    tenant_id=st.one_of(st.none(), st.text(min_size=1, max_size=30)),
    source=st.text(min_size=1, max_size=40),
    event_type=st.text(min_size=1, max_size=40),
)
def test_cloudevent_roundtrip_fuzz(
    order_id: str,
    user_id: str,
    amount: float,
    is_active: bool,
    tags: list[str],
    correlation_id: str | None,
    tenant_id: str | None,
    source: str,
    event_type: str,
):
    original = FuzzOrderEvent(
        order_id=order_id,
        user_id=user_id,
        amount=amount,
        is_active=is_active,
        tags=tags,
    )

    corr_token = None
    if correlation_id:
        corr_token = set_correlation_id(correlation_id)

    user_token = None
    if tenant_id:
        user_token = set_user_context(
            UserContext(user_id="test_user", tenant_id=tenant_id)
        )

    try:
        ce = to_cloudevent(
            original,
            source=source,
            event_type=event_type,
        )

        # 1. Roundtrip from CloudEvent instance
        reconstructed = from_cloudevent(ce, FuzzOrderEvent)
        assert reconstructed == original

        # 2. Roundtrip from JSON string
        json_str = cloudevent_to_json(ce)
        reconstructed_from_json = from_cloudevent(json_str, FuzzOrderEvent)
        assert reconstructed_from_json == original

        # 3. Roundtrip from dictionary
        ce_dict = cloudevent_to_dict(ce)
        reconstructed_from_dict = from_cloudevent(ce_dict, FuzzOrderEvent)
        assert reconstructed_from_dict == original

        # 4. Conversion to typed CloudEventEnvelope
        envelope = to_envelope(original, source=source, event_type=event_type)
        assert isinstance(envelope, CloudEventEnvelope)
        assert envelope.source == source
        assert envelope.type == event_type
        assert envelope.data == original.model_dump(mode="json")
        if correlation_id:
            assert envelope.correlationid == correlation_id
        if tenant_id:
            assert envelope.tenantid == tenant_id

    finally:
        if corr_token:
            correlation_id_ctx.reset(corr_token)
        if user_token:
            user_ctx.reset(user_token)
