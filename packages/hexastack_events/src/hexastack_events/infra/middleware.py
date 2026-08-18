import inspect
import uuid
from collections.abc import Callable
from datetime import UTC, datetime
from typing import Any, cast

from hexastack_core.domain import Event, Generic
from hexastack_core.utils.context import get_correlation_id, get_user_context
from hexastack_events.domain.models import OutboxRecord
from hexastack_events.ports.outbox import OutboxStoragePort


class OutboxCaptureMiddleware:
    """CQRS middleware capturing emitted events into the Transactional Outbox.

    Notes/Architectural Intent:
        Intercepts Event messages or results to stage OutboxRecord instances in
        OutboxStoragePort, guaranteeing at-least-once cross-service delivery.
    """

    def __init__(
        self,
        storage: OutboxStoragePort,
        source: str = "hexastack",
        enabled: bool = True,
    ) -> None:
        self._storage = storage
        self._source = source
        self._enabled = enabled

    def __call__[G: Generic, R](
        self,
        instance: G,
        next_call: Callable[[G], R],
    ) -> R:
        """Intercept message execution and stage event if message is an Event instance.

        Args:
            instance: Dispatched message instance.
            next_call: Next middleware or handler in chain.

        Returns:
            Handler execution result.
        """
        if self._enabled and isinstance(instance, Event):
            self._stage_event(instance)

        result = next_call(instance)

        if inspect.isawaitable(result):

            async def _async_wrap() -> Any:
                res = await result
                if self._enabled and isinstance(res, Event):
                    self._stage_event(res)
                return res

            return cast("R", _async_wrap())

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
