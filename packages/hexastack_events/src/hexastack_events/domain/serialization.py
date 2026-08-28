"""High-performance serialization and deserialization engine using msgspec.

Notes/Architectural Intent:
    Provides ultra-low-latency JSON and MessagePack encoders/decoders for CloudEvents
    and Outbox payloads with schema-cached encoders and zero-copy byte buffer handling.
"""

from __future__ import annotations

from typing import Any, TypeVar

import msgspec

from hexastack_events.domain.models import CloudEventEnvelope

T = TypeVar("T")

__all__ = [
    "decode_cloudevent_bytes",
    "decode_cloudevent_msgpack",
    "encode_cloudevent_bytes",
    "encode_cloudevent_msgpack",
    "MsgspecEnvelopeSerializer",
]

_JSON_ENCODER = msgspec.json.Encoder()
_MSGPACK_ENCODER = msgspec.msgpack.Encoder()

_CLOUDEVENT_JSON_DECODER = msgspec.json.Decoder(type=dict[str, Any])
_CLOUDEVENT_MSGPACK_DECODER = msgspec.msgpack.Decoder(type=dict[str, Any])


def encode_cloudevent_bytes(envelope: CloudEventEnvelope | dict[str, Any]) -> bytes:
    """Encode a CloudEvent envelope to optimized UTF-8 JSON bytes using msgspec.

    Args:
        envelope: CloudEventEnvelope instance or raw dictionary.

    Returns:
        UTF-8 encoded JSON bytes.

    Raises:
        msgspec.EncodeError: If payload contains non-serializable objects.
    """
    if isinstance(envelope, CloudEventEnvelope):
        return _JSON_ENCODER.encode(envelope.model_dump())
    return _JSON_ENCODER.encode(envelope)


def decode_cloudevent_bytes(data: bytes | bytearray) -> dict[str, Any]:
    """Decode UTF-8 JSON bytes into a CloudEvent dictionary using msgspec.

    Args:
        data: UTF-8 encoded JSON bytes buffer.

    Returns:
        Dictionary representation of CloudEvent.

    Raises:
        msgspec.DecodeError: If byte stream is not valid JSON.
    """
    return _CLOUDEVENT_JSON_DECODER.decode(data)


def encode_cloudevent_msgpack(envelope: CloudEventEnvelope | dict[str, Any]) -> bytes:
    """Encode a CloudEvent envelope to binary MessagePack format using msgspec.

    Args:
        envelope: CloudEventEnvelope instance or raw dictionary.

    Returns:
        Binary MessagePack bytes.

    Raises:
        msgspec.EncodeError: If payload cannot be encoded to MessagePack.
    """
    if isinstance(envelope, CloudEventEnvelope):
        return _MSGPACK_ENCODER.encode(envelope.model_dump())
    return _MSGPACK_ENCODER.encode(envelope)


def decode_cloudevent_msgpack(data: bytes | bytearray) -> dict[str, Any]:
    """Decode MessagePack binary payload into a CloudEvent dictionary using msgspec.

    Args:
        data: Raw MessagePack byte buffer.

    Returns:
        Dictionary representation of CloudEvent.

    Raises:
        msgspec.DecodeError: If byte stream is not valid MessagePack.
    """
    return _CLOUDEVENT_MSGPACK_DECODER.decode(data)


class MsgspecEnvelopeSerializer:
    """Fast serialization and envelope bundling adapter powered by msgspec.

    Notes/Architectural Intent:
        Wraps OutboxRecord payloads and CloudEvent envelopes into standardized,
        high-throughput byte buffers supporting both JSON and MessagePack formats.
    """

    def __init__(self, use_msgpack: bool = False) -> None:
        """Initialize serializer with chosen wire format.

        Args:
            use_msgpack: If True, uses MessagePack binary serialization; otherwise UTF-8 JSON.
        """
        self._use_msgpack = use_msgpack

    def serialize_envelope(self, envelope: CloudEventEnvelope) -> bytes:
        """Serialize CloudEvent envelope into wire format bytes.

        Args:
            envelope: CloudEventEnvelope domain instance.

        Returns:
            Encoded bytes.
        """
        if self._use_msgpack:
            return encode_cloudevent_msgpack(envelope)
        return encode_cloudevent_bytes(envelope)

    def deserialize_envelope(self, data: bytes) -> CloudEventEnvelope:
        """Deserialize wire format bytes back into CloudEventEnvelope domain instance.

        Args:
            data: Raw wire format byte buffer.

        Returns:
            Instantiated CloudEventEnvelope.
        """
        if self._use_msgpack:
            raw_dict = decode_cloudevent_msgpack(data)
        else:
            raw_dict = decode_cloudevent_bytes(data)
        return CloudEventEnvelope.model_validate(raw_dict)
