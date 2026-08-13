from hexastack_core.domain import Event
from hexastack_events.adapters.cloudevents import from_cloudevent, to_cloudevent
from hypothesis import given
from hypothesis import strategies as st


class FuzzOrderEvent(Event):
    order_id: str
    user_id: str
    amount: float


@given(
    order_id=st.text(min_size=1, max_size=50),
    user_id=st.text(min_size=1, max_size=50),
    amount=st.floats(min_value=0.0, max_value=1_000_000.0, allow_nan=False),
)
def test_cloudevent_roundtrip_fuzz(order_id: str, user_id: str, amount: float):
    original = FuzzOrderEvent(order_id=order_id, user_id=user_id, amount=amount)
    ce = to_cloudevent(
        original,
        source="https://hexastack.io/orders",
        event_type="io.hexastack.order.fuzz",
    )

    reconstructed = from_cloudevent(ce, FuzzOrderEvent)
    assert reconstructed.order_id == original.order_id
    assert reconstructed.user_id == original.user_id
    assert reconstructed.amount == original.amount
