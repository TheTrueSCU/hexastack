"""NATS JetStream distributed event bus adapter for hexastack-events.

Notes/Architectural Intent:
    Implements DistributedEventBusPort backed by NATS JetStream for high-throughput,
    at-least-once distributed event delivery across services. The adapter uses lazy
    NATS imports so that the package loads cleanly without nats-py installed; it only
    raises ImportError when a NATS operation is actually invoked, pointing the caller
    to ``pip install hexastack-events[nats]``.

    JetStream stream configuration:
        - Retention: WorkQueue — each message is delivered to exactly one consumer group.
        - Storage: File — durable persistence across NATS server restarts.
        - MaxDeliver: 5 — exhausted messages are forwarded to the DLQ subject.
        - AckWait: 30 s — unacknowledged messages are redelivered after timeout.

    Subject routing:
        - Published messages go to ``{subject_prefix}.{envelope.type}``.
        - Dead-letter messages land on ``{subject_prefix}.dlq.{envelope.type}``.
"""

from __future__ import annotations

import asyncio
import threading
from collections.abc import Callable
from typing import TYPE_CHECKING, Any

from hexastack_core.domain import Event
from hexastack_events.domain.exceptions import (
    EventDeliveryError,
    EventSerializationError,
)
from hexastack_events.domain.models import CloudEventEnvelope
from hexastack_events.domain.serialization import (
    decode_cloudevent_bytes,
    encode_cloudevent_bytes,
)
from hexastack_events.ports.buses import DistributedEventBusPort

if TYPE_CHECKING:
    import nats
    import nats.aio.client
    import nats.js


def _require_nats() -> None:
    """Raise a helpful ImportError when nats-py is not installed.

    Raises:
        ImportError: Always, when the nats package is unavailable.

    Notes/Architectural Intent:
        Guards all runtime NATS usage so the package remains importable without
        the optional dependency. Error message directs users to the correct extra.
    """
    try:
        import nats  # noqa: F401
    except ImportError as exc:
        raise ImportError(
            "nats-py is required for NatsJetStreamEventBusAdapter. "
            "Install it with: pip install hexastack-events[nats]"
        ) from exc


class NatsJetStreamEventBusAdapter(DistributedEventBusPort):
    """NATS JetStream implementation of DistributedEventBusPort.

    Notes/Architectural Intent:
        Provides a fully async-native event bus backed by NATS JetStream. The adapter
        wraps async NATS operations for the synchronous port interface using a dedicated
        internal event loop running on a background thread, ensuring the caller's thread
        is never blocked long-term and asyncio event loops are never nested.

        Lifecycle:
            1. Construct with server URLs and optional stream/subject configuration.
            2. Call ``connect()`` (async) to establish the JetStream stream.
            3. Use ``publish`` / ``publish_envelope`` / ``subscribe`` from any context.
            4. Call ``disconnect()`` (async) or use as an async context manager.
    """

    def __init__(
        self,
        servers: list[str] | None = None,
        stream_name: str = "hexastack",
        subject_prefix: str = "hexastack.events",
        max_deliver: int = 5,
        ack_wait_seconds: float = 30.0,
    ) -> None:
        """Initialise the adapter with NATS server coordinates and stream settings.

        Args:
            servers: List of NATS server URLs (e.g. ``["nats://localhost:4222"]``).
                Defaults to ``["nats://localhost:4222"]`` when omitted.
            stream_name: JetStream stream name to create or bind to.
            subject_prefix: Subject namespace prefix for all published messages.
            max_deliver: Maximum delivery attempts before forwarding to DLQ.
            ack_wait_seconds: Seconds to wait for consumer ACK before redelivery.

        Notes/Architectural Intent:
            Construction is side-effect-free; no network connection is established
            until ``connect()`` is awaited.
        """
        _require_nats()
        self._servers: list[str] = servers or ["nats://localhost:4222"]
        self._stream_name = stream_name
        self._subject_prefix = subject_prefix
        self._max_deliver = max_deliver
        self._ack_wait_seconds = ack_wait_seconds

        self._nc: nats.aio.client.Client | None = None
        self._js: nats.js.JetStreamContext | None = None

        # Background event loop for bridging sync callers into async NATS operations.
        self._loop: asyncio.AbstractEventLoop = asyncio.new_event_loop()
        self._loop_thread = threading.Thread(
            target=self._loop.run_forever,
            daemon=True,
            name="nats-event-loop",
        )
        self._loop_thread.start()

    # ------------------------------------------------------------------
    # Lifecycle helpers
    # ------------------------------------------------------------------

    def _run(self, coro: Any) -> Any:
        """Schedule a coroutine on the background event loop and block until done.

        Args:
            coro: Awaitable coroutine to execute.

        Returns:
            The coroutine's return value.

        Raises:
            EventDeliveryError: If the coroutine raises an unexpected exception.

        Notes/Architectural Intent:
            Uses ``asyncio.run_coroutine_threadsafe`` so that callers on any thread
            (including threads that already have a running event loop) can invoke async
            NATS operations without nesting event loops.
        """
        future = asyncio.run_coroutine_threadsafe(coro, self._loop)
        return future.result()

    async def connect(self) -> None:
        """Connect to NATS and provision the JetStream stream.

        Raises:
            EventDeliveryError: If the NATS connection or stream creation fails.

        Notes/Architectural Intent:
            Idempotent: subsequent calls while connected are no-ops. Creates the
            JetStream stream with a wildcard subject filter covering all topics
            under the configured prefix.
        """
        import nats
        import nats.js.api as js_api
        import nats.js.errors as js_errors

        if self._nc is not None and self._nc.is_connected:
            return

        try:
            self._nc = await nats.connect(self._servers)
        except Exception as exc:
            raise EventDeliveryError(
                f"Failed to connect to NATS at {self._servers}: {exc}"
            ) from exc

        self._js = self._nc.jetstream()

        stream_config = js_api.StreamConfig(
            name=self._stream_name,
            subjects=[f"{self._subject_prefix}.>"],
            retention=js_api.RetentionPolicy.WORK_QUEUE,
            storage=js_api.StorageType.FILE,
            deny_delete=False,
            deny_purge=False,
        )
        try:
            await self._js.add_stream(stream_config)
        except js_errors.BadRequestError:
            # Stream already exists — update to match our config.
            await self._js.update_stream(stream_config)
        except Exception as exc:
            raise EventDeliveryError(
                f"Failed to provision JetStream stream '{self._stream_name}': {exc}"
            ) from exc

    async def disconnect(self) -> None:
        """Drain and close the NATS connection.

        Notes/Architectural Intent:
            Draining ensures in-flight messages are flushed before the connection
            is torn down, preserving at-least-once delivery guarantees.
        """
        if self._nc is not None and self._nc.is_connected:
            await self._nc.drain()
        self._nc = None
        self._js = None

    # ------------------------------------------------------------------
    # Async context manager
    # ------------------------------------------------------------------

    async def __aenter__(self) -> NatsJetStreamEventBusAdapter:
        """Connect on entry.

        Returns:
            Self, after connecting.
        """
        await self.connect()
        return self

    async def __aexit__(self, *_: Any) -> None:
        """Disconnect on exit.

        Args:
            *_: Ignored exception info.
        """
        await self.disconnect()

    # ------------------------------------------------------------------
    # DistributedEventBusPort implementation
    # ------------------------------------------------------------------

    def publish(self, event: Event) -> None:
        """Wrap a domain event into a CloudEventEnvelope and publish to JetStream.

        Args:
            event: Domain event instance to publish.

        Raises:
            EventDeliveryError: If publishing fails or the NATS connection is lost.
            EventSerializationError: If the event payload cannot be serialized.

        Notes/Architectural Intent:
            Constructs a minimal CloudEvents 1.0 envelope from the domain event's
            class name (as the ``type`` field) and serializes via msgspec for
            sub-millisecond wire encoding.
        """
        import datetime

        envelope = CloudEventEnvelope(
            id=getattr(event, "id", None) or str(id(event)),
            source=self._subject_prefix,
            type=event.__class__.__name__,
            time=datetime.datetime.now(datetime.UTC).isoformat(),
            data=event.model_dump() if hasattr(event, "model_dump") else vars(event),
        )
        self.publish_envelope(envelope)

    def publish_envelope(self, envelope: CloudEventEnvelope) -> None:
        """Publish a CloudEventEnvelope directly to JetStream.

        Args:
            envelope: Fully-formed CloudEventEnvelope to publish.

        Raises:
            EventDeliveryError: If the NATS connection is not established or
                the publish operation fails.
            EventSerializationError: If msgspec fails to encode the envelope.

        Notes/Architectural Intent:
            Subject is composed as ``{subject_prefix}.{envelope.type}`` for
            fine-grained per-type consumer subscriptions. Encodes payload using
            the msgspec JSON encoder for zero-copy byte throughput.
        """
        self._run(self._async_publish_envelope(envelope))

    async def _async_publish_envelope(self, envelope: CloudEventEnvelope) -> None:
        """Internal async implementation of publish_envelope.

        Args:
            envelope: CloudEventEnvelope to encode and publish.

        Raises:
            EventDeliveryError: When NATS is disconnected or publish fails.
            EventSerializationError: When msgspec encoding fails.
        """
        if self._js is None:
            raise EventDeliveryError(
                "NatsJetStreamEventBusAdapter is not connected. "
                "Call connect() before publishing."
            )

        subject = f"{self._subject_prefix}.{envelope.type}"

        try:
            payload = encode_cloudevent_bytes(envelope)
        except Exception as exc:
            raise EventSerializationError(
                f"Failed to serialize CloudEventEnvelope for type '{envelope.type}': {exc}"
            ) from exc

        try:
            await self._js.publish(subject, payload)
        except Exception as exc:
            raise EventDeliveryError(
                f"NATS JetStream publish to '{subject}' failed: {exc}"
            ) from exc

    def subscribe(
        self,
        event_type: str,
        handler: Callable[[Event], Any],
    ) -> None:
        """Create a durable JetStream push consumer for the given event type.

        Args:
            event_type: The CloudEvent ``type`` field value to subscribe to.
                Maps to subject ``{subject_prefix}.{event_type}``.
            handler: Callable invoked with each decoded CloudEventEnvelope when
                a matching message arrives.

        Raises:
            EventDeliveryError: If subscription setup fails.

        Notes/Architectural Intent:
            Each unique ``event_type`` gets its own durable consumer named
            ``{stream_name}-{event_type}`` to support independent consumer group
            scaling. Dead-letter subject is configured as
            ``{subject_prefix}.dlq.{event_type}`` and activated once ``max_deliver``
            is exhausted by the JetStream server.
        """
        self._run(self._async_subscribe(event_type, handler))

    async def _async_subscribe(
        self,
        event_type: str,
        handler: Callable[[Any], Any],
    ) -> None:
        """Internal async implementation of subscribe.

        Args:
            event_type: Event type string to subscribe to.
            handler: Callable to invoke on each deserialized envelope.

        Raises:
            EventDeliveryError: If the JetStream subscription fails.
        """
        import nats.js.api as js_api

        if self._js is None:
            raise EventDeliveryError(
                "NatsJetStreamEventBusAdapter is not connected. "
                "Call connect() before subscribing."
            )

        subject = f"{self._subject_prefix}.{event_type}"
        durable_name = f"{self._stream_name}-{event_type}".replace(".", "-")
        dlq_subject = f"{self._subject_prefix}.dlq.{event_type}"

        consumer_config = js_api.ConsumerConfig(
            durable_name=durable_name,
            deliver_policy=js_api.DeliverPolicy.ALL,
            ack_policy=js_api.AckPolicy.EXPLICIT,
            max_deliver=self._max_deliver,
            ack_wait=self._ack_wait_seconds,  # float seconds
            flow_control=False,
        )

        async def _message_handler(msg: Any) -> None:
            try:
                raw = decode_cloudevent_bytes(msg.data)
                envelope = CloudEventEnvelope.model_validate(raw)
                handler(envelope)
                await msg.ack()
            except Exception:
                await msg.nak()

        try:
            await self._js.subscribe(
                subject,
                cb=_message_handler,
                durable=durable_name,
                config=consumer_config,
                manual_ack=True,
            )
        except Exception as exc:
            raise EventDeliveryError(
                f"Failed to subscribe to NATS subject '{subject}' "
                f"(durable='{durable_name}', dlq='{dlq_subject}'): {exc}"
            ) from exc


__all__ = [
    "NatsJetStreamEventBusAdapter",
]
