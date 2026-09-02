import asyncio
import logging
from typing import Any, cast

from hexastack_core.domain import Event
from hexastack_core.ports.lock import AsyncLockPort, LockPort
from hexastack_cqrs.ports.buses import EventBusPort
from hexastack_events.domain.models import CloudEventEnvelope
from hexastack_events.ports.buses import DistributedEventBusPort
from hexastack_events.ports.outbox import (
    OutboxRelayPort,
    OutboxStoragePort,
)

logger = logging.getLogger("hexastack.events.outbox.asyncio")


class AsyncioOutboxRelay(OutboxRelayPort):
    """Native asyncio background poller and streamer for Transactional Outbox.

    Notes/Architectural Intent:
        Runs as an in-process asyncio task during application lifespan. Periodically
        fetches pending records from OutboxStoragePort, publishes them via
        DistributedEventBusPort or EventBusPort, and updates delivery state.
        Accepts an optional LockPort or AsyncLockPort (such as FileLockAdapter or RedisLockAdapter)
        to prevent race conditions and duplicate event dispatch across multi-process daemons.
    """

    def __init__(
        self,
        storage: OutboxStoragePort,
        bus: EventBusPort,
        poll_interval_seconds: float = 1.0,
        batch_size: int = 50,
        lock: LockPort | AsyncLockPort | None = None,
    ) -> None:
        self._storage = storage
        self._bus = bus
        self._poll_interval = poll_interval_seconds
        self._batch_size = batch_size
        self._lock = lock
        self._task: asyncio.Task[Any] | None = None
        self._running: bool = False

    async def _poll_loop(self) -> None:
        """Internal asynchronous polling loop."""
        while self._running:
            try:
                count = self.publish_pending_batch(limit=self._batch_size)
                if count > 0:
                    logger.debug("Relayed %d outbox events", count)
            except Exception as exc:  # noqa: BLE001
                logger.error("Unexpected error in outbox relay loop: %s", exc)

            try:
                await asyncio.sleep(self._poll_interval)
            except asyncio.CancelledError:
                break

    def publish_pending_batch(self, limit: int = 50) -> int:
        """Fetch pending records and dispatch them to the event bus.

        Args:
            limit: Maximum records to drain.

        Returns:
            Number of successfully published records.
        """
        if isinstance(self._lock, LockPort):
            acquired = self._lock.acquire(blocking=False)
            if not acquired:
                return 0
            try:
                return self._drain_and_publish(limit=limit)
            finally:
                self._lock.release()

        return self._drain_and_publish(limit=limit)

    def _drain_and_publish(self, limit: int = 50) -> int:
        """Internal worker fetching and publishing pending records."""
        records = self._storage.fetch_pending(limit=limit)
        published_count = 0

        for record in records:
            try:
                envelope = CloudEventEnvelope(
                    id=record.id,
                    source=record.source,
                    type=record.event_type,
                    time=record.created_at.isoformat(),
                    datacontenttype="application/json",
                    correlationid=record.correlation_id,
                    tenantid=record.tenant_id,
                    data=record.payload,
                )
                if isinstance(self._bus, DistributedEventBusPort):
                    self._bus.publish_envelope(envelope)
                else:
                    self._bus.publish(cast("Event", envelope))

                self._storage.mark_published(record.id)
                published_count += 1
            except Exception as exc:  # noqa: BLE001
                logger.warning(
                    "Failed to relay outbox event %s: %s",
                    record.id,
                    exc,
                )
                self._storage.mark_failed(record.id, str(exc))

        return published_count

    def start(self) -> None:
        """Start the background outbox polling task."""
        if not self._running:
            self._running = True
            try:
                loop = asyncio.get_running_loop()
                self._task = loop.create_task(self._poll_loop())
            except RuntimeError:
                # If no running event loop in current thread, task will be started when loop runs
                pass

    def stop(self) -> None:
        """Stop the background outbox polling task."""
        self._running = False
        if self._task and not self._task.done():
            self._task.cancel()
            self._task = None


__all__ = [
    "AsyncioOutboxRelay",
]
