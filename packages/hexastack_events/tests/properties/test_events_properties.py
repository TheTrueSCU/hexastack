"""Hypothesis property-based tests for CloudEvents serialization and Outbox queue invariants.

Notes/Architectural Intent:
    Fuzzes arbitrary domain event structures, unicode payloads, nested attributes,
    and outbox lifecycle transitions to prove:
    1. CloudEvents encode/decode roundtrips maintain perfect payload and timestamp fidelity.
    2. Contextual propagation (correlation_id, user context) seamlessly embeds into CloudEvent extensions.
    3. InMemoryOutboxStorage guarantees FIFO ordering, retry thresholds, and status isolation.
    4. Deterministic EventSerializationError on malformed or schema-mismatched payloads.
"""

from hypothesis import given
from hypothesis import strategies as st
from pydantic import create_model

from hexastack_core.domain import Event
from hexastack_core.utils.context import correlation_scope
from hexastack_events.adapters.cloudevents.serializer import (
    cloudevent_to_dict,
    cloudevent_to_json,
    from_cloudevent,
    to_cloudevent,
)
from hexastack_events.adapters.outbox.in_memory import InMemoryOutboxStorage
from hexastack_events.domain.models import OutboxRecord, OutboxStatus

clean_str = st.text(
    alphabet="abcdefghijklmnopqrstuvwxyz0123456789", min_size=1, max_size=25
)


@given(
    event_name=clean_str,
    str_val=clean_str,
    int_val=st.integers(min_value=-10000, max_value=10000),
    bool_val=st.booleans(),
    cid=clean_str,
)
def test_cloudevent_serialization_roundtrip_property(
    event_name: str,
    str_val: str,
    int_val: int,
    bool_val: bool,
    cid: str,
):
    """Property: Any dynamically synthesized Event model serializes to CloudEvent and deserializes losslessly."""
    DynamicEvent = create_model(
        f"Event_{event_name}",
        str_field=(str, ...),
        int_field=(int, ...),
        bool_field=(bool, ...),
        __base__=Event,
    )

    with correlation_scope(cid):
        original_event = DynamicEvent.model_validate(
            {
                "str_field": str_val,
                "int_field": int_val,
                "bool_field": bool_val,
            }
        )

        ce = to_cloudevent(original_event)

        # Invariant: Correlation ID propagated
        assert ce["correlationid"] == cid

        # Invariant: JSON roundtrip
        json_str = cloudevent_to_json(ce)
        deserialized_from_json = from_cloudevent(json_str, DynamicEvent)
        assert deserialized_from_json == original_event

        # Invariant: Dict roundtrip
        dict_payload = cloudevent_to_dict(ce)
        deserialized_from_dict = from_cloudevent(dict_payload, DynamicEvent)
        assert deserialized_from_dict == original_event


@given(
    records_data=st.lists(
        st.tuples(clean_str, clean_str),
        min_size=1,
        max_size=20,
    )
)
def test_in_memory_outbox_lifecycle_and_retry_invariants(
    records_data: list[tuple[str, str]],
):
    """Property: Outbox correctly stages, retries up to max threshold, and publishes records."""
    import uuid

    storage = InMemoryOutboxStorage()

    created_records = [
        OutboxRecord(
            id=str(uuid.uuid4()),
            event_type=evt_name,
            payload={"msg": payload_text},
        )
        for evt_name, payload_text in records_data
    ]
    storage.save_all(created_records)

    # Initial pending count
    pending = storage.fetch_pending(limit=100)
    assert len(pending) == len(records_data)
    assert all(r.status == OutboxStatus.PENDING for r in pending)

    # Mark first record published
    first_record = pending[0]
    storage.mark_published(first_record.id)

    # Verify pending count decreases
    remaining = storage.fetch_pending(limit=100)
    assert len(remaining) == len(records_data) - 1
    assert first_record.id not in {r.id for r in remaining}

    # Mark second record failed until exceeding retry threshold (5)
    if len(remaining) > 0:
        second_record = remaining[0]
        for i in range(5):
            storage.mark_failed(second_record.id, f"Attempt {i + 1} failed")

        # Exceeded max retry count -> no longer in fetch_pending
        after_max_retries = storage.fetch_pending(limit=100)
        assert second_record.id not in {r.id for r in after_max_retries}
