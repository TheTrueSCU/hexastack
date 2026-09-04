"""Domain package init for hexastack_events."""

from hexastack_events.domain.context import EventContext
from hexastack_events.domain.exceptions import (
    DuplicateEventError,
    EventDeliveryError,
    EventError,
    EventSerializationError,
    OutboxError,
)
from hexastack_events.domain.models import (
    CloudEventEnvelope,
    OutboxRecord,
    OutboxStatus,
)
from hexastack_events.domain.serialization import (
    MsgspecEnvelopeSerializer,
    decode_cloudevent_bytes,
    decode_cloudevent_msgpack,
    encode_cloudevent_bytes,
    encode_cloudevent_msgpack,
)
from hexastack_events.domain.streams import (
    StreamMessage,
    StreamPartitionOffset,
)
from hexastack_events.domain.tasks import (
    TaskRecord,
    TaskState,
)

__all__ = [
    "CloudEventEnvelope",
    "decode_cloudevent_bytes",
    "decode_cloudevent_msgpack",
    "DuplicateEventError",
    "encode_cloudevent_bytes",
    "encode_cloudevent_msgpack",
    "EventContext",
    "EventDeliveryError",
    "EventError",
    "EventSerializationError",
    "MsgspecEnvelopeSerializer",
    "OutboxError",
    "OutboxRecord",
    "OutboxStatus",
    "StreamMessage",
    "StreamPartitionOffset",
    "TaskRecord",
    "TaskState",
]
