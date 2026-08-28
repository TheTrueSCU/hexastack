"""Unit tests for msgspec-powered CloudEvent and Outbox serialization."""

from hexastack_events.domain.models import CloudEventEnvelope
from hexastack_events.domain.serialization import (
    MsgspecEnvelopeSerializer,
    decode_cloudevent_bytes,
    decode_cloudevent_msgpack,
    encode_cloudevent_bytes,
    encode_cloudevent_msgpack,
)


def test_msgspec_json_roundtrip():
    envelope = CloudEventEnvelope(
        id="evt-12345",
        source="https://hexastack.dev/orders",
        type="order.created.v1",
        time="2026-08-28T07:00:00Z",
        correlationid="corr-abc-99",
        tenantid="tenant-acme",
        data={"order_id": "ord-99", "amount": 149.99, "items": ["sku-1", "sku-2"]},
    )

    # 1. Direct byte encoding from envelope
    raw_bytes = encode_cloudevent_bytes(envelope)
    assert isinstance(raw_bytes, bytes)
    assert b"order.created.v1" in raw_bytes

    # 2. Direct byte encoding from dictionary
    dict_bytes = encode_cloudevent_bytes(envelope.model_dump())
    assert isinstance(dict_bytes, bytes)

    # 3. Decoding
    decoded = decode_cloudevent_bytes(raw_bytes)
    assert decoded["id"] == "evt-12345"
    assert decoded["data"]["amount"] == 149.99
    assert decoded["correlationid"] == "corr-abc-99"


def test_msgspec_msgpack_roundtrip():
    envelope = CloudEventEnvelope(
        id="evt-msgpack-1",
        source="https://hexastack.dev/payments",
        type="payment.processed.v1",
        time="2026-08-28T07:05:00Z",
        data={"payment_id": "pay-777", "status": "settled"},
    )

    # 1. Binary MessagePack encoding from envelope
    msgpack_bytes = encode_cloudevent_msgpack(envelope)
    assert isinstance(msgpack_bytes, bytes)

    # 2. Binary MessagePack encoding from dictionary
    dict_mp_bytes = encode_cloudevent_msgpack(envelope.model_dump())
    assert isinstance(dict_mp_bytes, bytes)

    # 3. Binary MessagePack decoding
    decoded = decode_cloudevent_msgpack(msgpack_bytes)
    assert decoded["id"] == "evt-msgpack-1"
    assert decoded["data"]["payment_id"] == "pay-777"
    assert decoded["data"]["status"] == "settled"


def test_msgspec_envelope_serializer_adapter():
    json_serializer = MsgspecEnvelopeSerializer(use_msgpack=False)
    msgpack_serializer = MsgspecEnvelopeSerializer(use_msgpack=True)

    envelope = CloudEventEnvelope(
        id="evt-serializer-test",
        source="hexastack.test",
        type="test.event",
        time="2026-08-28T07:10:00Z",
        data={"test": True, "count": 42},
    )

    # JSON serializer adapter roundtrip
    json_bytes = json_serializer.serialize_envelope(envelope)
    restored_json = json_serializer.deserialize_envelope(json_bytes)
    assert restored_json.id == envelope.id
    assert restored_json.data == envelope.data

    # Msgpack serializer adapter roundtrip
    mp_bytes = msgpack_serializer.serialize_envelope(envelope)
    restored_mp = msgpack_serializer.deserialize_envelope(mp_bytes)
    assert restored_mp.id == envelope.id
    assert restored_mp.data == envelope.data
