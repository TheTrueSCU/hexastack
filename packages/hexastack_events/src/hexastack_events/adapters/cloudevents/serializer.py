import json
import uuid
from datetime import UTC, datetime
from typing import Any

from cloudevents.v1.http import CloudEvent, from_dict, from_json
from hexastack_core.domain import Event
from hexastack_core.utils.context import get_correlation_id, get_user_context

from hexastack_events.domain.exceptions import EventSerializationError
from hexastack_events.domain.models import CloudEventEnvelope


def to_cloudevent(
    event: Event,
    *,
    source: str = "hexastack",
    event_type: str | None = None,
    event_id: str | None = None,
    time: datetime | None = None,
    extensions: dict[str, Any] | None = None,
) -> CloudEvent:
    """Wrap a domain Event into a standard CNCF CloudEvent envelope.

    Notes/Architectural Intent:
        Standardizes domain event serialization for cross-service, cloud-native
        messaging. Automatically extracts active correlation_id and tenant_id
        from context into CloudEvents extension attributes.

    Args:
        event: Domain Event Pydantic model instance.
        source: URI identifier of the event producer (defaults to 'hexastack').
        event_type: Event type string (defaults to event class name).
        event_id: Unique event ID (defaults to new UUID4).
        time: Event timestamp in UTC (defaults to current UTC datetime).
        extensions: Optional custom extension attributes.

    Returns:
        Populated CNCF CloudEvent instance.
    """
    now = time or datetime.now(UTC)
    cid = get_correlation_id()
    user_ctx = get_user_context()

    attributes: dict[str, Any] = {
        "id": event_id or str(uuid.uuid4()),
        "source": source,
        "type": event_type or event.__class__.__name__,
        "specversion": "1.0",
        "time": now.isoformat(),
        "datacontenttype": "application/json",
    }

    if cid:
        attributes["correlationid"] = cid

    if user_ctx and user_ctx.tenant_id:
        attributes["tenantid"] = user_ctx.tenant_id

    if extensions:
        attributes.update(extensions)

    data = event.model_dump(mode="json")
    return CloudEvent(attributes, data)


def from_cloudevent[T: Event](
    cloudevent_data: CloudEvent | dict[str, Any] | str,
    event_cls: type[T],
) -> T:
    """Deserialize a CloudEvent envelope or JSON payload into a typed domain Event.

    Notes/Architectural Intent:
        Reconstructs the domain Event model from CloudEvent data payload while
        preserving structural validation via Pydantic model_validate.

    Args:
        cloudevent_data: CloudEvent instance, dictionary payload, or JSON string.
        event_cls: Target Event class to instantiate.

    Returns:
        Instantiated and validated domain Event model.

    Raises:
        EventSerializationError: If deserialization fails.
    """
    try:
        if isinstance(cloudevent_data, str):
            ce = from_json(cloudevent_data)
        elif isinstance(cloudevent_data, dict):
            ce = from_dict(cloudevent_data)
        else:
            ce = cloudevent_data

        payload = ce.data
        if isinstance(payload, str):
            payload = json.loads(payload)

        return event_cls.model_validate(payload)
    except Exception as exc:
        raise EventSerializationError(
            f"Failed to deserialize CloudEvent into '{event_cls.__name__}': {exc}"
        ) from exc


def to_envelope(
    event: Event,
    *,
    source: str = "hexastack",
    event_type: str | None = None,
    event_id: str | None = None,
) -> CloudEventEnvelope:
    """Convert domain Event to a typed CloudEventEnvelope Pydantic model.

    Args:
        event: Domain Event instance.
        source: Event source URI.
        event_type: Event type identifier.
        event_id: Optional unique event ID.

    Returns:
        Populated CloudEventEnvelope instance.
    """
    ce = to_cloudevent(event, source=source, event_type=event_type, event_id=event_id)
    attrs = ce.get_attributes()
    return CloudEventEnvelope(
        id=str(attrs.get("id")),
        source=str(attrs.get("source")),
        type=str(attrs.get("type")),
        time=str(attrs.get("time")),
        datacontenttype=str(attrs.get("datacontenttype", "application/json")),
        correlationid=attrs.get("correlationid"),
        tenantid=attrs.get("tenantid"),
        data=ce.data if isinstance(ce.data, dict) else {},
    )


def cloudevent_to_dict(ce: CloudEvent) -> dict[str, Any]:
    """Serialize a CloudEvent instance to a standard dictionary format."""
    result = dict(ce.get_attributes())
    result["data"] = ce.data
    return result


def cloudevent_to_json(ce: CloudEvent) -> str:
    """Serialize a CloudEvent instance to a valid JSON string."""
    return json.dumps(cloudevent_to_dict(ce))


__all__ = [
    "cloudevent_to_dict",
    "cloudevent_to_json",
    "from_cloudevent",
    "to_cloudevent",
    "to_envelope",
]
