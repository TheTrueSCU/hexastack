import asyncio
import logging
from typing import Any, cast

from hexastack_core.ports.lock import AsyncLockPort, LockPort
from hexastack_core.ports.logging import LoggingPort
from hexastack_cqrs.ports.buses import EventBusPort
from hexastack_events.domain.models import CloudEventEnvelope
from hexastack_events.ports.buses import DistributedEventBusPort
from hexastack_events.ports.outbox import (
    OutboxRelayPort,
    OutboxStoragePort,
)

_fallback_logger = logging.getLogger("hexastack.events.outbox.asyncio")


class AsyncioOutboxRelay(OutboxRelayPort):
    """Native asyncio background poller and streamer for Transactional Outbox.

    Notes/Architectural Intent:
        Runs as an in-process asyncio task during application lifespan. Periodically
        fetches pending records from OutboxStoragePort, publishes them via
        DistributedEventBusPort or EventBusPort, and updates delivery state.
        Accepts an optional LockPort or AsyncLockPort (such as FileLockAdapter or RedisLockAdapter)
        to prevent race conditions and duplicate event dispatch across multi-process daemons.
        Optionally receives a LoggingPort for unified structured telemetry.
    """

    def __init__(
        self,
        storage: OutboxStoragePort,
        bus: EventBusPort,
        poll_interval_seconds: float = 1.0,
        batch_size: int = 50,
        lock: LockPort | AsyncLockPort | None = None,
        logger: LoggingPort | None = None,
    ) -> None:
        self._storage = storage
        self._bus = bus
        self._poll_interval = poll_interval_seconds
        self._batch_size = batch_size
        self._lock = lock
        self._logger = logger
        self._task: asyncio.Task[Any] | None = None
        self._running: bool = False

    def _log_debug(self, message: str) -> None:
        """Emit debug message to LoggingPort or fallback logger."""
        if self._logger is not None:
            self._logger.debug(message)
        else:
            _fallback_logger.debug(message)

    def _log_error(self, message: str) -> None:
        """Emit error message to LoggingPort or fallback logger."""
        if self._logger is not None:
            self._logger.error(message)
        else:
            _fallback_logger.error(message)

    def _log_warning(self, message: str) -> None:
        """Emit warning message to LoggingPort or fallback logger."""
        if self._logger is not None:
            self._logger.warning(message)
        else:
            _fallback_logger.warning(message)

    async def _poll_loop(self) -> None:
        """Internal asynchronous polling loop."""
        while self._running:
            try:
                count = await self.publish_pending_batch_async(limit=self._batch_size)
                if count > 0:
                    self._log_debug(f"Relayed {count} outbox events")
            except Exception as exc:  # noqa: BLE001
                self._log_error(f"Unexpected error in outbox relay loop: {exc}")

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

        Raises:
            TypeError: If configured with an AsyncLockPort which cannot be acquired synchronously.
        """
        if isinstance(self._lock, AsyncLockPort):
            raise TypeError(
                "AsyncLockPort cannot be acquired synchronously in publish_pending_batch(); "
                "use publish_pending_batch_async() or provide a synchronous LockPort."
            )
        if isinstance(self._lock, LockPort):
            acquired = self._lock.acquire(blocking=False)
            if not acquired:
                return 0
            try:
                return self._drain_and_publish(limit=limit)
            finally:
                self._lock.release()

        return self._drain_and_publish(limit=limit)

    async def publish_pending_batch_async(self, limit: int = 50) -> int:
        """Fetch pending records and dispatch them to the event bus asynchronously.

        Args:
            limit: Maximum records to drain.

        Returns:
            Number of successfully published records.
        """
        if isinstance(self._lock, AsyncLockPort):
            acquired = await self._lock.acquire(blocking=False)
            if not acquired:
                return 0
            try:
                return self._drain_and_publish(limit=limit)
            finally:
                await self._lock.release()
        elif isinstance(self._lock, LockPort):
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
                    self._bus.publish(cast("Any", envelope))

                self._storage.mark_published(record.id)
                published_count += 1
            except Exception as exc:  # noqa: BLE001
                self._log_warning(f"Failed to relay outbox event {record.id}: {exc}")
                self._storage.mark_failed(record.id, str(exc))

        return published_count

    def start(self) -> None:
        """Start the background outbox polling task.

        Notes/Architectural Intent:
            Idempotent: Only transitions _running to True when an active event loop
            is present and the background polling task is successfully scheduled.
        """
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            # No running event loop in current thread; avoid marking as running
            return

        if not self._running or self._task is None or self._task.done():
            self._running = True
            self._task = loop.create_task(self._poll_loop())

    def stop(self) -> None:
        """Stop the background outbox polling task."""
        self._running = False
        if self._task and not self._task.done():
            self._task.cancel()
            self._task = None


__all__ = [
    "AsyncioOutboxRelay",
]
