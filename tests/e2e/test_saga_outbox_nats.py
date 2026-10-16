"""End-to-End integration test and feature journey for Distributed Saga, Outbox, and NATS JetStream.

Notes/Architectural Intent:
    Validates the enterprise Distributed Saga pattern (HS-05 / Issue #210) coordinating
    an e-commerce checkout transaction across hexagonal layers:
    1. Hexaflow Workflow orchestrating the multi-step checkout saga.
    2. SQLAlchemy Transactional Outbox atomically staging CloudEvents.
    3. Asyncio Outbox Relay polling and delivering CloudEvents over NATS JetStream.
    4. Distributed OpenTelemetry trace cascades preserving correlation across boundaries.
    5. Automatic reverse compensation unwinding when payment processing fails.
"""

from __future__ import annotations

import asyncio
import uuid
from collections.abc import Generator
from concurrent.futures import ThreadPoolExecutor
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from hexaflow import Workflow, WorkflowStatus
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from hexastack_core.domain import Event
from hexastack_events.adapters.buses.nats import NatsJetStreamEventBusAdapter
from hexastack_events.adapters.outbox.asyncio import AsyncioOutboxRelay
from hexastack_events.adapters.outbox.sqlalchemy import (
    Base,
    SqlAlchemyOutboxStorage,
)
from hexastack_events.domain.models import (
    CloudEventEnvelope,
    OutboxRecord,
    OutboxStatus,
)
from hexastack_events.domain.serialization import decode_cloudevent_bytes
from hexastack_otel.adapters.tracing.in_memory import InMemoryTracingAdapter


def _run_in_thread_if_loop_active(func: Any, *args: Any, **kwargs: Any) -> Any:
    """Execute callable offloaded to thread pool if an asyncio event loop is active on current thread."""
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        loop = None

    if loop is not None and loop.is_running():
        with ThreadPoolExecutor(max_workers=1) as pool:
            return pool.submit(func, *args, **kwargs).result()
    return func(*args, **kwargs)


# ---------------------------------------------------------------------------
# Domain Events & Models
# ---------------------------------------------------------------------------


class OrderCreatedEvent(Event):
    """Domain event emitted upon successful order placement and outbox staging."""

    order_id: str
    customer_id: str
    total_amount: float
    items: list[str]
    trace_id: str


class OrderCancelledEvent(Event):
    """Compensating domain event emitted when checkout saga is unwound on failure."""

    order_id: str
    reason: str
    trace_id: str


# ---------------------------------------------------------------------------
# Test Fixtures & In-Memory Infrastructure
# ---------------------------------------------------------------------------


@pytest.fixture
def sqlite_outbox_storage() -> Generator[SqlAlchemyOutboxStorage]:
    """Provide clean in-memory SQLite database session and SqlAlchemyOutboxStorage."""
    engine = create_engine("sqlite:///:memory:", echo=False)
    Base.metadata.create_all(engine)
    session_factory = sessionmaker(bind=engine)
    storage = SqlAlchemyOutboxStorage(session_factory=session_factory)
    yield storage
    Base.metadata.drop_all(engine)
    engine.dispose()


@pytest.fixture
def in_memory_tracer() -> Generator[InMemoryTracingAdapter]:
    """Provide an isolated InMemoryTracingAdapter capturing span cascades."""
    tracer = InMemoryTracingAdapter()
    yield tracer
    tracer.shutdown()


@pytest.fixture
def nats_test_harness() -> Generator[
    tuple[NatsJetStreamEventBusAdapter, list[tuple[str, bytes]]]
]:
    """Provide mocked NATS JetStream harness capturing published subjects and payloads."""
    published_messages: list[tuple[str, bytes]] = []

    mock_nc = MagicMock()
    mock_nc.is_connected = True
    mock_nc.drain = AsyncMock()

    mock_js = MagicMock()
    mock_js.add_stream = AsyncMock()
    mock_js.update_stream = AsyncMock()

    async def _mock_publish(subject: str, payload: bytes) -> Any:
        published_messages.append((subject, payload))
        ack = MagicMock()
        ack.stream = "hexastack"
        ack.seq = len(published_messages)
        return ack

    mock_js.publish = AsyncMock(side_effect=_mock_publish)
    mock_nc.jetstream = MagicMock(return_value=mock_js)

    with patch("nats.connect", AsyncMock(return_value=mock_nc)):
        adapter = NatsJetStreamEventBusAdapter(
            servers=["nats://localhost:4222"],
            stream_name="hexastack-ecommerce",
            subject_prefix="hexastack.events",
        )
        adapter._run(adapter.connect())
        yield adapter, published_messages
        adapter._run(adapter.disconnect())


# ---------------------------------------------------------------------------
# Distributed Saga Factory
# ---------------------------------------------------------------------------


def create_checkout_saga(
    outbox_storage: SqlAlchemyOutboxStorage,
    tracer: InMemoryTracingAdapter,
    order_data: dict[str, Any],
    simulate_payment_failure: bool = False,
) -> Workflow:
    """Construct an e-commerce checkout saga workflow using Hexaflow DAG.

    Args:
        outbox_storage: SqlAlchemyOutboxStorage for transactional event persistence.
        tracer: InMemoryTracingAdapter for distributed trace cascade recording.
        order_data: Input order details (order_id, customer_id, items, total_amount).
        simulate_payment_failure: Whether to simulate payment decline triggering compensation.

    Returns:
        Configured Hexaflow Workflow with step dependencies and compensation handlers.
    """
    wf = Workflow(name="ecommerce-checkout-saga", version="1.0.0")

    @wf.step(
        name="validate_cart",
        description="Step 1: Validate cart items and calculate totals",
        dry_run=lambda: {"order_id": order_data["order_id"], "valid": True},
    )
    def validate_cart() -> dict[str, Any]:
        with tracer.trace_scope("saga.validate_cart") as span:
            span.set_attribute("order.id", order_data["order_id"])
            return {
                "order_id": order_data["order_id"],
                "customer_id": order_data["customer_id"],
                "items": order_data["items"],
                "total_amount": order_data["total_amount"],
                "validated": True,
            }

    def compensate_inventory() -> None:
        """Compensation handler for Step 2: Release reserved inventory stock."""
        with tracer.trace_scope("saga.compensate_inventory") as span:
            span.set_attribute("order.id", order_data["order_id"])
            # Stage compensating OrderCancelledEvent to transactional outbox
            cancel_event = OrderCancelledEvent(
                order_id=order_data["order_id"],
                reason="Payment processing failure",
                trace_id=span.context.trace_id,
            )
            cancel_record = OutboxRecord(
                id=str(uuid.uuid4()),
                event_type="OrderCancelledEvent",
                payload={
                    "order_id": cancel_event.order_id,
                    "reason": cancel_event.reason,
                    "trace_id": cancel_event.trace_id,
                },
                source="hexastack.ecommerce.saga",
                correlation_id=order_data["correlation_id"],
            )
            outbox_storage.save(cancel_record)

    @wf.step(
        name="reserve_inventory",
        depends_on=["validate_cart"],
        description="Step 2: Reserve inventory stock for order items",
        compensation=compensate_inventory,
        dry_run=lambda validate_cart=None: {"reserved": True},
    )
    def reserve_inventory(
        validate_cart: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        with tracer.trace_scope("saga.reserve_inventory") as span:
            span.set_attribute("order.id", order_data["order_id"])
            return {"reserved": True, "items": order_data["items"]}

    @wf.step(
        name="process_payment",
        depends_on=["reserve_inventory"],
        description="Step 3: Charge customer payment gateway",
        dry_run=lambda reserve_inventory=None: {
            "charged": not simulate_payment_failure
        },
    )
    def process_payment(
        reserve_inventory: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        with tracer.trace_scope("saga.process_payment") as span:
            span.set_attribute("order.id", order_data["order_id"])
            if simulate_payment_failure:
                raise RuntimeError("Payment declined: Insufficient funds")
            return {"charged": True, "amount": order_data["total_amount"]}

    @wf.step(
        name="stage_order_outbox",
        depends_on=["process_payment"],
        description="Step 4: Atomically persist order and stage OrderCreated CloudEvent in Outbox",
        dry_run=lambda process_payment=None: {"staged": True},
    )
    def stage_order_outbox(
        process_payment: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        with tracer.trace_scope("saga.stage_order_outbox") as span:
            span.set_attribute("order.id", order_data["order_id"])
            created_event = OrderCreatedEvent(
                order_id=order_data["order_id"],
                customer_id=order_data["customer_id"],
                total_amount=order_data["total_amount"],
                items=order_data["items"],
                trace_id=span.context.trace_id,
            )
            outbox_record = OutboxRecord(
                id=str(uuid.uuid4()),
                event_type="OrderCreatedEvent",
                payload={
                    "order_id": created_event.order_id,
                    "customer_id": created_event.customer_id,
                    "total_amount": created_event.total_amount,
                    "items": created_event.items,
                    "trace_id": created_event.trace_id,
                },
                source="hexastack.ecommerce.saga",
                correlation_id=order_data["correlation_id"],
            )
            outbox_storage.save(outbox_record)
            return {"staged": True, "record_id": outbox_record.id}

    return wf


# ---------------------------------------------------------------------------
# Test Cases
# ---------------------------------------------------------------------------


@pytest.mark.e2e
def test_checkout_saga_happy_path(
    sqlite_outbox_storage: SqlAlchemyOutboxStorage,
    in_memory_tracer: InMemoryTracingAdapter,
    nats_test_harness: tuple[NatsJetStreamEventBusAdapter, list[tuple[str, bytes]]],
) -> None:
    """Verify end-to-end checkout saga execution, outbox staging, and NATS JetStream delivery.

    Args:
        sqlite_outbox_storage: In-memory SQLAlchemy outbox storage fixture.
        in_memory_tracer: In-memory OpenTelemetry tracer fixture.
        nats_test_harness: Connected NATS adapter and published message capture list.

    Notes/Architectural Intent:
        Demonstrates the complete happy-path cascade:
        1. Checkout saga executes through Hexaflow DAG stages.
        2. OrderCreated event is atomically staged in SQLite outbox storage.
        3. AsyncioOutboxRelay drains pending outbox records and emits CloudEvents 1.0 JSON.
        4. NATS JetStream receives message on 'hexastack.events.OrderCreatedEvent'.
        5. Trace cascade spans link the entire execution under a common correlation context.
    """
    nats_adapter, published_messages = nats_test_harness
    outbox_relay = AsyncioOutboxRelay(
        storage=sqlite_outbox_storage,
        bus=nats_adapter,
        batch_size=10,
    )

    order_id = f"ord-{uuid.uuid4().hex[:8]}"
    correlation_id = f"corr-{uuid.uuid4().hex[:12]}"
    order_data = {
        "order_id": order_id,
        "customer_id": "cust-alice-42",
        "items": ["sku-laptop-x1", "sku-wireless-mouse"],
        "total_amount": 1499.50,
        "correlation_id": correlation_id,
    }

    # Step 1: Execute checkout saga workflow
    saga = create_checkout_saga(
        outbox_storage=sqlite_outbox_storage,
        tracer=in_memory_tracer,
        order_data=order_data,
        simulate_payment_failure=False,
    )
    result = _run_in_thread_if_loop_active(saga.run)

    result_status = result.status
    assert result_status == WorkflowStatus.COMPLETED

    # Step 2: Verify outbox storage has 1 pending record
    pending = sqlite_outbox_storage.fetch_pending(limit=10)
    pending_count = len(pending)
    assert pending_count == 1

    staged_record = pending[0]
    event_type = staged_record.event_type
    assert event_type == "OrderCreatedEvent"

    record_status = staged_record.status
    assert record_status == OutboxStatus.PENDING

    record_corr_id = staged_record.correlation_id
    assert record_corr_id == correlation_id

    # Step 3: Drain outbox via AsyncioOutboxRelay
    relayed_count = outbox_relay.publish_pending_batch(limit=10)
    assert relayed_count == 1

    # Verify outbox record transitioned to PUBLISHED status
    with sqlite_outbox_storage._session_scope() as session:
        from hexastack_events.adapters.outbox.sqlalchemy import OutboxEventBaseModel

        db_record = session.get(OutboxEventBaseModel, staged_record.id)
        assert db_record is not None
        updated_status = db_record.status
        assert updated_status == OutboxStatus.PUBLISHED.value

    # Verify no more pending records
    rem_pending = len(sqlite_outbox_storage.fetch_pending(limit=10))
    assert rem_pending == 0

    # Step 4: Verify NATS JetStream published message
    published_count = len(published_messages)
    assert published_count == 1

    subject, raw_payload = published_messages[0]
    expected_subject = "hexastack.events.OrderCreatedEvent"
    assert subject == expected_subject

    # Step 5: Decode and validate CloudEvents 1.0 envelope structure
    envelope = CloudEventEnvelope.model_validate(decode_cloudevent_bytes(raw_payload))
    envelope_type = envelope.type
    assert envelope_type == "OrderCreatedEvent"

    envelope_source = envelope.source
    assert envelope_source == "hexastack.ecommerce.saga"

    envelope_corr_id = envelope.correlationid
    assert envelope_corr_id == correlation_id

    payload_data = envelope.data
    assert isinstance(payload_data, dict)
    delivered_order_id = payload_data.get("order_id")
    assert delivered_order_id == order_id

    delivered_amount = payload_data.get("total_amount")
    assert delivered_amount == 1499.50

    # Step 6: Verify OpenTelemetry trace cascade
    spans = in_memory_tracer.finished_spans
    span_count = len(spans)
    assert span_count == 4

    span_names = [s.name for s in spans]
    assert "saga.validate_cart" in span_names
    assert "saga.reserve_inventory" in span_names
    assert "saga.process_payment" in span_names
    assert "saga.stage_order_outbox" in span_names


@pytest.mark.e2e
def test_checkout_saga_compensation_on_failure(
    sqlite_outbox_storage: SqlAlchemyOutboxStorage,
    in_memory_tracer: InMemoryTracingAdapter,
    nats_test_harness: tuple[NatsJetStreamEventBusAdapter, list[tuple[str, bytes]]],
) -> None:
    """Verify saga failure unwinds via compensation and stages OrderCancelledEvent in Outbox.

    Args:
        sqlite_outbox_storage: In-memory SQLAlchemy outbox storage fixture.
        in_memory_tracer: In-memory OpenTelemetry tracer fixture.
        nats_test_harness: Connected NATS adapter and published message capture list.

    Notes/Architectural Intent:
        When a downstream service (payment gateway) fails during saga execution,
        Hexaflow triggers reverse LIFO compensation. The inventory compensation
        handler stages a compensating OrderCancelledEvent into the Outbox, which
        is subsequently relayed to NATS JetStream to alert fulfillment services.
    """
    nats_adapter, published_messages = nats_test_harness
    outbox_relay = AsyncioOutboxRelay(
        storage=sqlite_outbox_storage,
        bus=nats_adapter,
        batch_size=10,
    )

    order_id = f"ord-{uuid.uuid4().hex[:8]}"
    correlation_id = f"corr-{uuid.uuid4().hex[:12]}"
    order_data = {
        "order_id": order_id,
        "customer_id": "cust-bob-99",
        "items": ["sku-standing-desk"],
        "total_amount": 750.00,
        "correlation_id": correlation_id,
    }

    # Step 1: Execute checkout saga with simulated payment failure
    saga = create_checkout_saga(
        outbox_storage=sqlite_outbox_storage,
        tracer=in_memory_tracer,
        order_data=order_data,
        simulate_payment_failure=True,
    )
    result = _run_in_thread_if_loop_active(saga.run)

    result_status = result.status
    assert result_status == WorkflowStatus.SUSPENDED

    # Trigger compensation unwinding across completed steps
    _run_in_thread_if_loop_active(saga.abort, result.run_id)

    # Step 2: Verify compensation staged OrderCancelledEvent into outbox
    pending = sqlite_outbox_storage.fetch_pending(limit=10)
    pending_count = len(pending)
    assert pending_count == 1

    cancel_record = pending[0]
    event_type = cancel_record.event_type
    assert event_type == "OrderCancelledEvent"

    cancel_payload = cancel_record.payload
    assert isinstance(cancel_payload, dict)
    cancelled_order_id = cancel_payload.get("order_id")
    assert cancelled_order_id == order_id

    cancel_reason = cancel_payload.get("reason")
    assert cancel_reason == "Payment processing failure"

    # Step 3: Relay compensating event over NATS JetStream
    relayed_count = outbox_relay.publish_pending_batch(limit=10)
    assert relayed_count == 1

    published_count = len(published_messages)
    assert published_count == 1

    subject, raw_payload = published_messages[0]
    expected_subject = "hexastack.events.OrderCancelledEvent"
    assert subject == expected_subject

    # Step 4: Validate CloudEvent envelope for compensating event
    envelope = CloudEventEnvelope.model_validate(decode_cloudevent_bytes(raw_payload))
    envelope_type = envelope.type
    assert envelope_type == "OrderCancelledEvent"

    envelope_corr_id = envelope.correlationid
    assert envelope_corr_id == correlation_id

    # Step 5: Verify compensation span was recorded in trace
    spans = in_memory_tracer.finished_spans
    span_names = [s.name for s in spans]
    assert "saga.compensate_inventory" in span_names


__all__ = [
    "test_checkout_saga_compensation_on_failure",
    "test_checkout_saga_happy_path",
]
