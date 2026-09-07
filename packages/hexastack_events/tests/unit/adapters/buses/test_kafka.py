"""Unit tests for KafkaDistributedEventBus adapter using mocked aiokafka client.

Notes/Architectural Intent:
    All Kafka network I/O is mocked so these tests execute reliably without requiring
    an external Kafka/Redpanda cluster or binary dependencies. Tests validate:
    1. Lazy loading & dependency enforcement (_require_kafka).
    2. CloudEvents 1.0 framing, headers, and binary msgspec serialization.
    3. Error handling, retries, and dead-letter queue (DLQ) topic routing.
    4. Async-to-sync background thread execution bridge.
    5. Consumer group lifecycle and explicit offset commit mechanisms.
"""

from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from hexastack_core.domain import Event
from hexastack_events.adapters.buses.kafka import KafkaDistributedEventBus
from hexastack_events.domain.exceptions import EventDeliveryError
from hexastack_events.domain.models import CloudEventEnvelope
from hexastack_events.domain.serialization import encode_cloudevent_bytes


class OrderPlacedEvent(Event):
    """Domain event used across Kafka adapter tests."""

    order_id: str
    total_amount: float


def _make_envelope(event_type: str = "OrderPlacedEvent") -> CloudEventEnvelope:
    """Construct a test CloudEventEnvelope instance."""
    return CloudEventEnvelope(
        id="kafka-evt-001",
        source="test.hexastack",
        type=event_type,
        time="2026-09-07T12:00:00+00:00",
        datacontenttype="application/json",
        correlationid="corr-123",
        tenantid="tenant-abc",
        data={"order_id": "ord-99", "total_amount": 149.99},
    )


@pytest.fixture
def mock_aiokafka_module():
    """Patch the aiokafka module with mock Producer and Consumer classes."""
    mock_producer = AsyncMock()
    mock_producer.start = AsyncMock()
    mock_producer.stop = AsyncMock()
    mock_producer.send_and_wait = AsyncMock()

    mock_consumer = AsyncMock()
    mock_consumer.start = AsyncMock()
    mock_consumer.stop = AsyncMock()
    mock_consumer.commit = AsyncMock()

    mock_aiokafka = MagicMock()
    mock_aiokafka.AIOKafkaProducer = MagicMock(return_value=mock_producer)
    mock_aiokafka.AIOKafkaConsumer = MagicMock(return_value=mock_consumer)

    with patch.dict("sys.modules", {"aiokafka": mock_aiokafka}):
        yield mock_aiokafka


def test_require_kafka_missing_dependency():
    """Verify informative ImportError is raised when aiokafka is not installed."""
    with (
        patch.dict("sys.modules", {"aiokafka": None}),
        pytest.raises(
            ImportError, match="aiokafka is required for KafkaDistributedEventBus"
        ),
    ):
        from hexastack_events.adapters.buses.kafka import _require_kafka

        _require_kafka()


def test_kafka_adapter_init(mock_aiokafka_module):
    """Verify adapter initialization settings and lazy connection state."""
    adapter = KafkaDistributedEventBus(
        bootstrap_servers=["broker1:9092", "broker2:9092"],
        client_id="custom-client",
        group_id="custom-group",
        topic_prefix="custom.events.",
        enable_dlq=True,
        max_retries=5,
    )
    assert adapter._bootstrap_servers == "broker1:9092,broker2:9092"
    assert adapter._client_id == "custom-client"
    assert adapter._group_id == "custom-group"
    assert adapter._topic_prefix == "custom.events"
    assert adapter._enable_dlq is True
    assert adapter._max_retries == 5
    assert adapter._is_connected is False
    adapter.close()


@pytest.mark.asyncio
async def test_kafka_adapter_connect_and_disconnect(mock_aiokafka_module):
    """Verify connect() starts the producer and disconnect() cleans up resources."""
    adapter = KafkaDistributedEventBus(bootstrap_servers="localhost:9092")
    try:
        await adapter.connect()
        assert adapter._is_connected is True
        mock_aiokafka_module.AIOKafkaProducer.return_value.start.assert_awaited_once()

        # Idempotent connect
        await adapter.connect()

        await adapter.disconnect()
        assert adapter._is_connected is False
        mock_aiokafka_module.AIOKafkaProducer.return_value.stop.assert_awaited_once()
    finally:
        adapter.close()


@pytest.mark.asyncio
async def test_kafka_adapter_context_manager(mock_aiokafka_module):
    """Verify async context manager connects on enter and disconnects on exit."""
    adapter = KafkaDistributedEventBus(bootstrap_servers="localhost:9092")
    try:
        async with adapter as bus:
            assert bus._is_connected is True
            mock_aiokafka_module.AIOKafkaProducer.return_value.start.assert_awaited_once()

        assert adapter._is_connected is False
    finally:
        adapter.close()


@pytest.mark.asyncio
async def test_kafka_adapter_connect_failure_raises_event_delivery_error(
    mock_aiokafka_module,
):
    """Verify connection errors are wrapped in EventDeliveryError."""
    mock_aiokafka_module.AIOKafkaProducer.return_value.start.side_effect = (
        ConnectionRefusedError("Broker unavailable")
    )

    adapter = KafkaDistributedEventBus(bootstrap_servers="invalid:9092")
    try:
        with pytest.raises(EventDeliveryError, match="Failed to connect to Kafka"):
            await adapter.connect()
    finally:
        adapter.close()


@pytest.mark.asyncio
async def test_kafka_adapter_publish_envelope_async(mock_aiokafka_module):
    """Verify publish_envelope_async sends encoded bytes and CloudEvents headers."""
    adapter = KafkaDistributedEventBus(
        bootstrap_servers="localhost:9092", topic_prefix="org.events"
    )
    try:
        await adapter.connect()
        envelope = _make_envelope()

        await adapter.publish_envelope_async(envelope)

        mock_producer = mock_aiokafka_module.AIOKafkaProducer.return_value
        mock_producer.send_and_wait.assert_awaited_once()

        call_kwargs = mock_producer.send_and_wait.call_args.kwargs
        assert call_kwargs["topic"] == "org.events.OrderPlacedEvent"
        assert call_kwargs["key"] == b"kafka-evt-001"
        assert isinstance(call_kwargs["value"], bytes)

        # Check CloudEvents header tuples
        headers_dict = dict(call_kwargs["headers"])
        assert headers_dict["ce_specversion"] == b"1.0"
        assert headers_dict["ce_id"] == b"kafka-evt-001"
        assert headers_dict["ce_type"] == b"OrderPlacedEvent"
        assert headers_dict["ce_correlationid"] == b"corr-123"
        assert headers_dict["ce_tenantid"] == b"tenant-abc"
    finally:
        adapter.close()


def test_kafka_adapter_sync_publish(mock_aiokafka_module):
    """Verify synchronous publish method works through the thread bridge."""
    adapter = KafkaDistributedEventBus(
        bootstrap_servers="localhost:9092", topic_prefix="sync.events"
    )
    try:
        event = OrderPlacedEvent(order_id="ord-1", total_amount=42.0)
        adapter.publish(event)

        mock_producer = mock_aiokafka_module.AIOKafkaProducer.return_value
        mock_producer.send_and_wait.assert_awaited_once()
        call_kwargs = mock_producer.send_and_wait.call_args.kwargs
        assert call_kwargs["topic"] == "sync.events.OrderPlacedEvent"
    finally:
        adapter.close()


@pytest.mark.asyncio
async def test_kafka_adapter_subscribe_and_consume_success(mock_aiokafka_module):
    """Verify subscribe_async registers a consumer and invokes handler on consumed messages."""
    envelope = _make_envelope("OrderPlacedEvent")
    raw_payload = encode_cloudevent_bytes(envelope)

    mock_msg = MagicMock()
    mock_msg.value = raw_payload
    mock_msg.key = b"kafka-evt-001"
    mock_msg.headers = []

    mock_consumer = AsyncMock()
    mock_consumer.start = AsyncMock()
    mock_consumer.stop = AsyncMock()
    mock_consumer.commit = AsyncMock()

    # Make consumer an async iterator yielding 1 message
    async def _mock_iter():
        yield mock_msg

    mock_consumer.__aiter__.side_effect = _mock_iter
    mock_aiokafka_module.AIOKafkaConsumer.return_value = mock_consumer

    handled_events: list[CloudEventEnvelope] = []

    async def handle_order(evt: CloudEventEnvelope) -> None:
        handled_events.append(evt)

    adapter = KafkaDistributedEventBus(bootstrap_servers="localhost:9092")
    try:
        await adapter.subscribe_async("OrderPlacedEvent", handle_order)

        # Allow consumer task to execute
        await asyncio.sleep(0.05)

        assert len(handled_events) == 1
        assert handled_events[0].id == "kafka-evt-001"
        assert handled_events[0].data["order_id"] == "ord-99"
        mock_consumer.commit.assert_awaited_once()
    finally:
        adapter.close()


@pytest.mark.asyncio
async def test_kafka_adapter_subscribe_dlq_routing_on_exhaustion(mock_aiokafka_module):
    """Verify messages exhausting retries are forwarded to the DLQ topic."""
    envelope = _make_envelope("FailingEvent")
    raw_payload = encode_cloudevent_bytes(envelope)

    mock_msg = MagicMock()
    mock_msg.value = raw_payload
    mock_msg.key = b"kafka-evt-001"
    mock_msg.headers = []

    mock_consumer = AsyncMock()
    mock_consumer.start = AsyncMock()
    mock_consumer.stop = AsyncMock()
    mock_consumer.commit = AsyncMock()

    async def _mock_iter():
        yield mock_msg

    mock_consumer.__aiter__.side_effect = _mock_iter
    mock_aiokafka_module.AIOKafkaConsumer.return_value = mock_consumer

    async def failing_handler(evt: CloudEventEnvelope) -> None:
        raise ValueError("Handler error forced")

    adapter = KafkaDistributedEventBus(
        bootstrap_servers="localhost:9092",
        topic_prefix="test.events",
        enable_dlq=True,
        max_retries=2,
    )
    try:
        await adapter.connect()
        await adapter.subscribe_async("FailingEvent", failing_handler)

        await asyncio.sleep(0.05)

        mock_producer = mock_aiokafka_module.AIOKafkaProducer.return_value
        # Check that DLQ send_and_wait was called
        dlq_calls = [
            c
            for c in mock_producer.send_and_wait.call_args_list
            if c.kwargs.get("topic") == "test.events.dlq.FailingEvent"
        ]
        assert len(dlq_calls) == 1
        mock_consumer.commit.assert_awaited_once()
    finally:
        adapter.close()


@pytest.mark.asyncio
async def test_kafka_adapter_publish_async(mock_aiokafka_module):
    """Verify publish_async automatically wraps domain event and publishes."""
    adapter = KafkaDistributedEventBus(bootstrap_servers="localhost:9092")
    try:
        event = OrderPlacedEvent(order_id="async-1", total_amount=10.0)
        await adapter.publish_async(event)

        mock_producer = mock_aiokafka_module.AIOKafkaProducer.return_value
        mock_producer.send_and_wait.assert_awaited_once()
        call_kwargs = mock_producer.send_and_wait.call_args.kwargs
        assert call_kwargs["topic"] == "hexastack.events.OrderPlacedEvent"
    finally:
        adapter.close()


def test_kafka_adapter_sync_subscribe(mock_aiokafka_module):
    """Verify synchronous subscribe method works through the thread bridge."""
    adapter = KafkaDistributedEventBus(bootstrap_servers="localhost:9092")
    try:
        mock_consumer = AsyncMock()
        mock_consumer.start = AsyncMock()
        mock_consumer.__aiter__.side_effect = lambda: iter([])
        mock_aiokafka_module.AIOKafkaConsumer.return_value = mock_consumer

        def sync_handler(evt: CloudEventEnvelope) -> None:
            pass

        adapter.subscribe("OrderPlacedEvent", sync_handler)
        mock_consumer.start.assert_awaited_once()
    finally:
        adapter.close()


@pytest.mark.asyncio
async def test_kafka_adapter_subscribe_invalid_payload_dlq(mock_aiokafka_module):
    """Verify malformed payload directly forwards to DLQ topic."""
    mock_msg = MagicMock()
    mock_msg.value = b"invalid-non-json-bytes"
    mock_msg.key = b"key"
    mock_msg.headers = []

    mock_consumer = AsyncMock()
    mock_consumer.start = AsyncMock()
    mock_consumer.commit = AsyncMock()

    async def _mock_iter():
        yield mock_msg

    mock_consumer.__aiter__.side_effect = _mock_iter
    mock_aiokafka_module.AIOKafkaConsumer.return_value = mock_consumer

    adapter = KafkaDistributedEventBus(
        bootstrap_servers="localhost:9092",
        topic_prefix="test.events",
        enable_dlq=True,
    )
    try:
        await adapter.connect()
        await adapter.subscribe_async("MalformedEvent", lambda _: None)

        await asyncio.sleep(0.05)

        mock_producer = mock_aiokafka_module.AIOKafkaProducer.return_value
        dlq_calls = [
            c
            for c in mock_producer.send_and_wait.call_args_list
            if c.kwargs.get("topic") == "test.events.dlq.MalformedEvent"
        ]
        assert len(dlq_calls) == 1
        mock_consumer.commit.assert_awaited_once()
    finally:
        adapter.close()


@pytest.mark.asyncio
async def test_kafka_adapter_sasl_and_ssl_configuration(mock_aiokafka_module):
    """Verify SASL credentials and SSLContext are correctly passed to producer and consumer."""
    dummy_ssl = MagicMock()
    mock_password = "app-password"  # pragma: allowlist secret
    adapter = KafkaDistributedEventBus(
        bootstrap_servers="secure.broker:9093",
        security_protocol="SASL_SSL",
        sasl_mechanism="SCRAM-SHA-512",
        sasl_plain_username="app-user",
        sasl_plain_password=mock_password,
        ssl_context=dummy_ssl,
    )
    try:
        await adapter.connect()
        producer_kwargs = mock_aiokafka_module.AIOKafkaProducer.call_args.kwargs
        assert producer_kwargs["security_protocol"] == "SASL_SSL"
        assert producer_kwargs["sasl_mechanism"] == "SCRAM-SHA-512"
        assert producer_kwargs["sasl_plain_username"] == "app-user"
        assert producer_kwargs["sasl_plain_password"] == mock_password
        assert producer_kwargs["ssl_context"] is dummy_ssl

        mock_consumer = AsyncMock()
        mock_consumer.start = AsyncMock()
        mock_consumer.__aiter__.side_effect = lambda: iter([])
        mock_aiokafka_module.AIOKafkaConsumer.return_value = mock_consumer

        await adapter.subscribe_async("SecureEvent", lambda _: None)
        consumer_kwargs = mock_aiokafka_module.AIOKafkaConsumer.call_args.kwargs
        assert consumer_kwargs["security_protocol"] == "SASL_SSL"
        assert consumer_kwargs["sasl_mechanism"] == "SCRAM-SHA-512"
        assert consumer_kwargs["ssl_context"] is dummy_ssl
    finally:
        adapter.close()


@pytest.mark.asyncio
async def test_kafka_adapter_publish_failure_raises_event_delivery_error(
    mock_aiokafka_module,
):
    """Verify producer send failure raises EventDeliveryError."""
    mock_aiokafka_module.AIOKafkaProducer.return_value.send_and_wait.side_effect = (
        RuntimeError("Broker write timeout")
    )

    adapter = KafkaDistributedEventBus(bootstrap_servers="localhost:9092")
    try:
        await adapter.connect()
        with pytest.raises(EventDeliveryError, match="Failed to publish event"):
            await adapter.publish_envelope_async(_make_envelope())
    finally:
        adapter.close()


@pytest.mark.asyncio
async def test_kafka_adapter_subscribe_failure_raises_event_delivery_error(
    mock_aiokafka_module,
):
    """Verify consumer start failure raises EventDeliveryError."""
    mock_aiokafka_module.AIOKafkaConsumer.return_value.start.side_effect = RuntimeError(
        "Consumer group coordinator unavailable"
    )

    adapter = KafkaDistributedEventBus(bootstrap_servers="localhost:9092")
    try:
        with pytest.raises(
            EventDeliveryError, match="Failed to subscribe Kafka consumer"
        ):
            await adapter.subscribe_async("TestEvent", lambda _: None)
    finally:
        adapter.close()
