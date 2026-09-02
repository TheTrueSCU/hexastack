import uuid
from datetime import UTC, datetime
from typing import Any

from hexastack_core.domain import Event, Generic
from hexastack_core.utils.context import get_correlation_id, get_user_context
from hexastack_cqrs.infra.middleware.generic import InOutMiddleware
from hexastack_events.domain.models import OutboxRecord
from hexastack_events.ports.outbox import OutboxStoragePort


class OutboxCaptureMiddleware(InOutMiddleware):
    """CQRS middleware capturing emitted events into the Transactional Outbox.

    Notes/Architectural Intent:
        Inherits from InOutMiddleware to intercept Event messages or results to
        stage OutboxRecord instances in OutboxStoragePort, guaranteeing at-least-once
        cross-service delivery across synchronous and asynchronous handlers.
    """

    def __init__(
        self,
        storage: OutboxStoragePort,
        source: str = "hexastack",
        enabled: bool = True,
    ) -> None:
        """Initialize outbox capture middleware with storage port, source, and enabled flag.

        Args:
            storage: OutboxStoragePort implementation.
            source: Source service identifier for staged OutboxRecord instances.
            enabled: Whether event capture is active.
        """
        self._storage = storage
        self._source = source
        self._enabled = enabled

    def before(self, instance: Generic) -> Any:
        """Stage event if the dispatched message instance is an Event.

        Args:
            instance: Dispatched command, query, or event message.

        Returns:
            None.
        """
        if self._enabled and isinstance(instance, Event):
            self._stage_event(instance)
        return None

    def after(self, instance: Generic, result: Any, context: Any) -> Any:
        """Stage event if the handler returned an Event instance.

        Args:
            instance: Dispatched message instance.
            result: Handler return value.
            context: Context object returned by before().

        Returns:
            Unmodified handler result.
        """
        if self._enabled and isinstance(result, Event):
            self._stage_event(result)
        return result

    def _stage_event(self, event: Event) -> None:
        """Helper to create and stage an OutboxRecord."""
        user_ctx = get_user_context()
        tenant_id = user_ctx.tenant_id if user_ctx is not None else None

        record = OutboxRecord(
            id=str(uuid.uuid4()),
            event_type=event.__class__.__name__,
            source=self._source,
            payload=event.model_dump(mode="json"),
            correlation_id=get_correlation_id(),
            tenant_id=tenant_id,
            created_at=datetime.now(UTC),
        )
        self._storage.save(record)


__all__ = [
    "OutboxCaptureMiddleware",
]
