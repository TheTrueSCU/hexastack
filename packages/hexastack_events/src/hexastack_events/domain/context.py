from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any


@dataclass(frozen=True)
class EventContext:
    """Contextual metadata accompanying an in-flight or received domain event.

    Notes/Architectural Intent:
        Represents the standard envelope attributes defined by CNCF CloudEvents 1.0,
        maintaining tracing correlation and multi-tenant partitioning.
    """

    event_id: str
    event_type: str
    source: str
    time: datetime = field(default_factory=lambda: datetime.now(UTC))
    datacontenttype: str = "application/json"
    correlation_id: str | None = None
    tenant_id: str | None = None
    extensions: dict[str, Any] = field(default_factory=dict)


__all__ = [
    "EventContext",
]
