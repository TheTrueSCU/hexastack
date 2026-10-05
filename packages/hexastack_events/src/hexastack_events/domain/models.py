from datetime import UTC, datetime
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field


class OutboxStatus(StrEnum):
    """Lifecycle status of an outbox event record."""

    PENDING = "PENDING"
    PUBLISHED = "PUBLISHED"
    FAILED = "FAILED"


class OutboxRecord(BaseModel):
    """Domain model representing a persistent outbox event awaiting relay delivery.

    Notes/Architectural Intent:
        Guarantees at-least-once delivery by recording uncommitted domain events
        within the same database transaction boundary as mutating state changes.
    """

    id: str = Field(description="Unique event/record identifier (UUID).")
    event_type: str = Field(
        description="String identifying the event class or schema type."
    )
    source: str = Field(
        default="hexastack",
        description="Producer identifier or service URI.",
    )
    payload: dict[str, Any] = Field(description="Serialized CloudEvent data payload.")
    status: OutboxStatus = Field(
        default=OutboxStatus.PENDING,
        description="Current delivery state.",
    )
    retry_count: int = Field(
        default=0,
        description="Number of failed delivery attempts.",
    )
    correlation_id: str | None = Field(
        default=None,
        description="Correlation ID for distributed tracing.",
    )
    tenant_id: str | None = Field(
        default=None,
        description="Tenant identifier for multi-tenant isolation.",
    )
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        description="Timestamp when event was staged in the outbox.",
    )
    published_at: datetime | None = Field(
        default=None,
        description="Timestamp when event was successfully dispatched to broker.",
    )
    last_error: str | None = Field(
        default=None,
        description="Last error message if a delivery attempt failed.",
    )

    def mark_failed(self, error_message: str) -> None:
        """Increment retry count and mark as failed."""
        self.retry_count += 1
        self.status = OutboxStatus.FAILED
        self.last_error = error_message

    def mark_published(self) -> None:
        """Mark record as successfully published."""
        self.status = OutboxStatus.PUBLISHED
        self.published_at = datetime.now(UTC)
        self.last_error = None


class CloudEventEnvelope(BaseModel):
    """Standardized CloudEvents 1.0 JSON envelope."""

    specversion: str = "1.0"
    id: str
    source: str
    type: str
    time: str
    datacontenttype: str = "application/json"
    correlationid: str | None = None
    tenantid: str | None = None
    data: dict[str, Any]


__all__ = [
    "CloudEventEnvelope",
    "OutboxRecord",
    "OutboxStatus",
]
