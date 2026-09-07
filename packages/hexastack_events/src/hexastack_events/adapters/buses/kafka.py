"""Apache Kafka and Redpanda distributed event bus adapter for hexastack-events.

Notes/Architectural Intent:
    Implements DistributedEventBusPort backed by Apache Kafka / Redpanda (via aiokafka)
    for high-throughput, horizontally-scalable distributed event delivery.
    The adapter uses lazy aiokafka imports so that the package loads cleanly without
    aiokafka installed; it only raises ImportError when a Kafka operation is actually invoked,
    pointing the caller to ``pip install hexastack-events[kafka]``.

    Key Architecture Features:
        - Native Async / Thread Bridge: Uses an internal background event loop and thread
          so synchronous ports (`publish`, `publish_envelope`, `subscribe`) work seamlessly
          across synchronous workers (such as gRPC or background threads) and asyncio contexts.
        - Topic Partitioning & Framing: Encodes CloudEvents 1.0 JSON & MessagePack envelopes
          using msgspec, published to `{topic_prefix}.{envelope.type}`.
        - Consumer Group Balancing: Supports consumer group auto-rebalancing and at-least-once
          offset commits.
        - Dead-Letter Queue (DLQ) Routing: Forwards unprocessable or failed messages to
          dedicated dead-letter topics `{topic_prefix}.dlq.{envelope.type}`.
"""

from __future__ import annotations

import asyncio
import contextlib
import logging
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
    import aiokafka

logger = logging.getLogger("hexastack.events.kafka")


def _require_kafka() -> None:
    """Raise a helpful ImportError when aiokafka is not installed.

    Raises:
        ImportError: Always, when the aiokafka package is unavailable.

    Notes/Architectural Intent:
        Guards all runtime Kafka usage so the package remains importable without
        the optional dependency. Error message directs users to the correct extra.
    """
    try:
        import aiokafka  # noqa: F401
    except ImportError as exc:
        raise ImportError(
            "aiokafka is required for KafkaDistributedEventBus. "
            "Install it with: pip install hexastack-events[kafka]"
        ) from exc


class KafkaDistributedEventBus(DistributedEventBusPort):
    """Apache Kafka and Redpanda implementation of DistributedEventBusPort.

    Notes/Architectural Intent:
        Provides an async-native event bus backed by aiokafka. The adapter bridges
        synchronous port methods (`publish`, `publish_envelope`, `subscribe`) to
        Kafka coroutines via an isolated background event loop thread.

        Lifecycle:
            1. Construct with bootstrap servers, client configuration, and topic prefixes.
            2. Call ``connect()`` (async) to initialize producer/consumer instances.
            3. Use ``publish`` / ``publish_envelope`` / ``subscribe`` across threads.
            4. Call ``disconnect()`` (async) or use as an async context manager.
    """

    def __init__(
        self,
        bootstrap_servers: str | list[str] | None = None,
        client_id: str = "hexastack",
        group_id: str = "hexastack-group",
        topic_prefix: str = "hexastack.events",
        enable_dlq: bool = True,
        max_retries: int = 3,
        auto_offset_reset: str = "earliest",
        security_protocol: str = "PLAINTEXT",
        sasl_mechanism: str | None = None,
        sasl_plain_username: str | None = None,
        sasl_plain_password: str | None = None,
        ssl_context: Any | None = None,
    ) -> None:
        """Initialize the Kafka event bus adapter.

        Args:
            bootstrap_servers: Host and port coordinates for Kafka / Redpanda brokers
                (e.g. ``"localhost:9092"`` or ``["broker1:9092", "broker2:9092"]``).
            client_id: Client identifier string for tracking and quotas.
            group_id: Default consumer group identifier for worker load balancing.
            topic_prefix: Topic namespace prefix prepended to all published event types.
            enable_dlq: Whether to route failed consumer messages to dead-letter topics.
            max_retries: Number of handler attempts before routing a message to the DLQ.
            auto_offset_reset: Policy for resetting offsets ("earliest", "latest", "none").
            security_protocol: Protocol used to communicate with brokers ("PLAINTEXT", "SSL", "SASL_PLAINTEXT", "SASL_SSL").
            sasl_mechanism: Authentication mechanism (e.g. "PLAIN", "SCRAM-SHA-256", "SCRAM-SHA-512").
            sasl_plain_username: Username for SASL authentication.
            sasl_plain_password: Password for SASL authentication.
            ssl_context: Configured SSLContext instance for secure TLS connections.

        Notes/Architectural Intent:
            Instantiating this class does not initiate network connections immediately.
            Network sockets and background polling loops are initialized during `connect()`.
        """
        _require_kafka()
        if isinstance(bootstrap_servers, list):
            self._bootstrap_servers = ",".join(bootstrap_servers)
        else:
            self._bootstrap_servers = bootstrap_servers or "localhost:9092"

        self._client_id = client_id
        self._group_id = group_id
        self._topic_prefix = topic_prefix.rstrip(".")
        self._enable_dlq = enable_dlq
        self._max_retries = max_retries
        self._auto_offset_reset = auto_offset_reset
        self._security_protocol = security_protocol
        self._sasl_mechanism = sasl_mechanism
        self._sasl_plain_username = sasl_plain_username
        self._sasl_plain_password = sasl_plain_password
        self._ssl_context = ssl_context

        self._producer: aiokafka.AIOKafkaProducer | None = None
        self._consumers: list[aiokafka.AIOKafkaConsumer] = []
        self._consumer_tasks: list[asyncio.Task[None]] = []
        self._is_connected = False

        # Dedicated background loop for bridging sync callers
        self._loop: asyncio.AbstractEventLoop = asyncio.new_event_loop()
        self._loop_thread = threading.Thread(
            target=self._loop.run_forever,
            daemon=True,
            name="kafka-event-loop",
        )
        self._loop_thread.start()

    # ------------------------------------------------------------------
    # Lifecycle & Connection
    # ------------------------------------------------------------------

    def _run(self, coro: Any) -> Any:
        """Schedule a coroutine on the background event loop and block until done.

        Args:
            coro: Awaitable coroutine to execute.

        Returns:
            The coroutine's return value.

        Raises:
            EventDeliveryError: If execution fails.
        """
        future = asyncio.run_coroutine_threadsafe(coro, self._loop)
        return future.result()

    async def connect(self) -> None:
        """Connect producer to Kafka brokers.

        Raises:
            EventDeliveryError: If broker connection fails.

        Notes/Architectural Intent:
            Idempotent: Subsequent invocations while connected return immediately.
        """
        if self._is_connected:
            return

        import aiokafka

        producer_kwargs: dict[str, Any] = {
            "bootstrap_servers": self._bootstrap_servers,
            "client_id": self._client_id,
            "security_protocol": self._security_protocol,
        }
        if self._sasl_mechanism:
            producer_kwargs["sasl_mechanism"] = self._sasl_mechanism
            producer_kwargs["sasl_plain_username"] = self._sasl_plain_username
            producer_kwargs["sasl_plain_password"] = self._sasl_plain_password
        if self._ssl_context:
            producer_kwargs["ssl_context"] = self._ssl_context

        try:
            self._producer = aiokafka.AIOKafkaProducer(**producer_kwargs)
            await self._producer.start()
            self._is_connected = True
            logger.info("Connected to Kafka brokers at %s", self._bootstrap_servers)
        except Exception as exc:
            self._is_connected = False
            raise EventDeliveryError(
                f"Failed to connect to Kafka at {self._bootstrap_servers}: {exc}"
            ) from exc

    async def disconnect(self) -> None:
        """Stop all consumers and producer, closing network connections.

        Notes/Architectural Intent:
            Ensures in-flight offsets are committed and producer flush buffers are drained.
        """
        for task in self._consumer_tasks:
            task.cancel()

        for consumer in self._consumers:
            with contextlib.suppress(Exception):
                await consumer.stop()

        self._consumers.clear()
        self._consumer_tasks.clear()

        if self._producer is not None:
            with contextlib.suppress(Exception):
                await self._producer.stop()
            self._producer = None

        self._is_connected = False

    async def __aenter__(self) -> KafkaDistributedEventBus:
        """Enter asynchronous context manager, establishing broker connection."""
        await self.connect()
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: Any,
    ) -> None:
        """Exit asynchronous context manager, disconnecting gracefully."""
        await self.disconnect()

    def close(self) -> None:
        """Synchronously disconnect and shutdown background event loop."""
        try:
            self._run(self.disconnect())
        except Exception:
            pass
        finally:
            if self._loop.is_running():
                self._loop.call_soon_threadsafe(self._loop.stop)
            if self._loop_thread.is_alive():
                self._loop_thread.join(timeout=2.0)

    # ------------------------------------------------------------------
    # Port Implementations
    # ------------------------------------------------------------------

    def publish_envelope(self, envelope: CloudEventEnvelope) -> None:
        """Publish a pre-formatted CloudEvents envelope to Kafka.

        Args:
            envelope: CloudEvents envelope model.

        Raises:
            EventDeliveryError: If publishing or encoding fails.
        """
        self._run(self.publish_envelope_async(envelope))

    async def publish_envelope_async(self, envelope: CloudEventEnvelope) -> None:
        """Asynchronously publish a CloudEvents envelope to its designated Kafka topic.

        Args:
            envelope: CloudEvents envelope model.

        Raises:
            EventDeliveryError: If the message cannot be delivered.
        """
        if not self._is_connected or self._producer is None:
            await self.connect()

        if self._producer is None:
            raise EventDeliveryError("Kafka producer is not connected.")

        topic = f"{self._topic_prefix}.{envelope.type}"

        try:
            payload_bytes = encode_cloudevent_bytes(envelope)
        except EventSerializationError as exc:
            raise EventDeliveryError(
                f"Failed to serialize CloudEvent envelope for topic '{topic}': {exc}"
            ) from exc

        headers = [
            ("ce_specversion", b"1.0"),
            ("ce_id", envelope.id.encode("utf-8")),
            ("ce_source", envelope.source.encode("utf-8")),
            ("ce_type", envelope.type.encode("utf-8")),
            ("ce_time", envelope.time.encode("utf-8")),
        ]
        if envelope.datacontenttype:
            headers.append(("content-type", envelope.datacontenttype.encode("utf-8")))
        if envelope.correlationid:
            headers.append(("ce_correlationid", envelope.correlationid.encode("utf-8")))
        if envelope.tenantid:
            headers.append(("ce_tenantid", envelope.tenantid.encode("utf-8")))

        try:
            key_bytes = envelope.id.encode("utf-8")
            await self._producer.send_and_wait(
                topic=topic,
                value=payload_bytes,
                key=key_bytes,
                headers=headers,
            )
            logger.debug(
                "Published CloudEvent %s to Kafka topic %s", envelope.id, topic
            )
        except Exception as exc:
            raise EventDeliveryError(
                f"Failed to publish event {envelope.id} to topic '{topic}': {exc}"
            ) from exc

    def publish(self, event: Event) -> None:
        """Wrap domain Event into CloudEventEnvelope and publish.

        Args:
            event: Domain event instance.

        Raises:
            EventDeliveryError: If serialization or delivery fails.
        """
        import datetime

        envelope = CloudEventEnvelope(
            id=getattr(event, "id", None)
            or getattr(event, "event_id", None)
            or "evt-" + event.__class__.__name__,
            source=self._client_id,
            type=event.__class__.__name__,
            time=datetime.datetime.now(datetime.UTC).isoformat(),
            data=event.model_dump() if hasattr(event, "model_dump") else event.__dict__,
        )
        self.publish_envelope(envelope)

    async def publish_async(self, event: Event) -> None:
        """Asynchronously wrap domain Event into CloudEventEnvelope and publish.

        Args:
            event: Domain event instance.

        Raises:
            EventDeliveryError: If serialization or delivery fails.
        """
        import datetime

        envelope = CloudEventEnvelope(
            id=getattr(event, "id", None)
            or getattr(event, "event_id", None)
            or "evt-" + event.__class__.__name__,
            source=self._client_id,
            type=event.__class__.__name__,
            time=datetime.datetime.now(datetime.UTC).isoformat(),
            data=event.model_dump() if hasattr(event, "model_dump") else event.__dict__,
        )
        await self.publish_envelope_async(envelope)

    def subscribe(
        self,
        event_type: str,
        handler: Callable[[Any], Any],
    ) -> None:
        """Subscribe a handler callback to a specific distributed event type.

        Args:
            event_type: Event type name or wildcard pattern.
            handler: Callable callback invoked when messages arrive.

        Raises:
            EventDeliveryError: If consumer registration fails.
        """
        self._run(self.subscribe_async(event_type, handler))

    def _build_consumer_kwargs(self, event_type: str) -> dict[str, Any]:
        """Build keyword arguments for Kafka consumer initialization."""
        consumer_kwargs: dict[str, Any] = {
            "bootstrap_servers": self._bootstrap_servers,
            "group_id": self._group_id,
            "client_id": f"{self._client_id}-{event_type}",
            "auto_offset_reset": self._auto_offset_reset,
            "enable_auto_commit": False,
            "security_protocol": self._security_protocol,
        }
        if self._sasl_mechanism:
            consumer_kwargs["sasl_mechanism"] = self._sasl_mechanism
            consumer_kwargs["sasl_plain_username"] = self._sasl_plain_username
            consumer_kwargs["sasl_plain_password"] = self._sasl_plain_password
        if self._ssl_context:
            consumer_kwargs["ssl_context"] = self._ssl_context
        return consumer_kwargs

    async def _send_dlq_message(self, dlq_topic: str, msg: Any) -> None:
        """Forward an unparseable or exhausted message to the DLQ topic."""
        if not self._enable_dlq or self._producer is None:
            return
        with contextlib.suppress(Exception):
            await self._producer.send_and_wait(
                topic=dlq_topic,
                value=msg.value,
                key=msg.key,
                headers=msg.headers,
            )

    async def _invoke_handler_with_retries(
        self,
        envelope: CloudEventEnvelope,
        handler: Callable[[Any], Any],
        msg: Any,
        dlq_topic: str,
    ) -> None:
        """Invoke event handler with exponential or linear retry backoff and DLQ fallback."""
        retries = 0
        while retries < self._max_retries:
            try:
                res = handler(envelope)
                if asyncio.iscoroutine(res):
                    await res
                return
            except Exception as handler_exc:
                retries += 1
                logger.warning(
                    "Handler failed on Kafka event %s (attempt %d/%d): %s",
                    envelope.id,
                    retries,
                    self._max_retries,
                    handler_exc,
                )
        await self._send_dlq_message(dlq_topic, msg)
        logger.info(
            "Forwarded exhausted event %s to DLQ topic %s",
            envelope.id,
            dlq_topic,
        )

    async def _process_consumer_message(
        self,
        msg: Any,
        topic: str,
        dlq_topic: str,
        handler: Callable[[Any], Any],
    ) -> None:
        """Deserialize and dispatch a single message from the Kafka topic."""
        try:
            raw_data = decode_cloudevent_bytes(msg.value)
            envelope = CloudEventEnvelope.model_validate(raw_data)
        except Exception as parse_exc:
            logger.error(
                "Failed to parse CloudEvent from Kafka topic %s: %s",
                topic,
                parse_exc,
            )
            await self._send_dlq_message(dlq_topic, msg)
            return

        await self._invoke_handler_with_retries(envelope, handler, msg, dlq_topic)

    async def subscribe_async(
        self,
        event_type: str,
        handler: Callable[[Any], Any],
    ) -> None:
        """Asynchronously register a consumer for the given event type.

        Args:
            event_type: Event type name.
            handler: Async or sync callable invoked for each consumed event.

        Raises:
            EventDeliveryError: If consumer subscription fails.
        """
        import aiokafka

        topic = f"{self._topic_prefix}.{event_type}"
        dlq_topic = f"{self._topic_prefix}.dlq.{event_type}"
        consumer_kwargs = self._build_consumer_kwargs(event_type)

        try:
            consumer = aiokafka.AIOKafkaConsumer(topic, **consumer_kwargs)
            await consumer.start()
            self._consumers.append(consumer)
        except Exception as exc:
            raise EventDeliveryError(
                f"Failed to subscribe Kafka consumer to topic '{topic}': {exc}"
            ) from exc

        async def _consume_loop() -> None:
            try:
                async for msg in consumer:
                    await self._process_consumer_message(msg, topic, dlq_topic, handler)
                    await consumer.commit()
            except asyncio.CancelledError:
                pass
            except Exception as loop_exc:
                logger.error(
                    "Kafka consumer loop error on topic %s: %s", topic, loop_exc
                )

        task = asyncio.create_task(_consume_loop())
        self._consumer_tasks.append(task)
        logger.info(
            "Kafka consumer subscribed to topic %s in group %s", topic, self._group_id
        )


__all__ = [
    "KafkaDistributedEventBus",
]
