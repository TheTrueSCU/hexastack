"""Unit tests for NatsJetStreamEventBusAdapter using mocked nats-py client.

Notes/Architectural Intent:
    All NATS I/O is mocked so these tests run without a real NATS server or
    the nats-py package installed. They validate the adapter's orchestration
    logic: subject routing, msgspec encoding, error propagation, and the
    async-to-sync bridge mechanism.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from hexastack_core.domain import Event
from hexastack_events.domain.exceptions import (
    EventDeliveryError,
)
from hexastack_events.domain.models import CloudEventEnvelope
from hexastack_events.domain.serialization import encode_cloudevent_bytes

# ---------------------------------------------------------------------------
# Helpers / stubs
# ---------------------------------------------------------------------------


class OrderCreatedEvent(Event):
    """Minimal domain event used across adapter tests."""

    order_id: str
    amount: float


def _make_envelope(event_type: str = "OrderCreatedEvent") -> CloudEventEnvelope:
    """Return a minimal CloudEventEnvelope for testing."""
    return CloudEventEnvelope(
        id="test-id-1",
        source="hexastack.events",
        type=event_type,
        time="2026-08-31T00:00:00+00:00",
        data={"order_id": "o-1", "amount": 99.9},
    )


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def mock_nats_module():
    """Patch the nats module with a minimal mock so nats-py need not be installed."""
    # jetstream() is SYNC in nats-py — use plain MagicMock, not AsyncMock.
    mock_js = MagicMock()
    mock_js.add_stream = AsyncMock()
    mock_js.update_stream = AsyncMock()
    mock_js.publish = AsyncMock()
    mock_js.subscribe = AsyncMock()

    mock_nc = AsyncMock()
    mock_nc.is_connected = True
    mock_nc.jetstream = MagicMock(return_value=mock_js)  # sync call

    mock_nats = MagicMock()
    mock_nats.connect = AsyncMock(return_value=mock_nc)

    # js_api stubs
    mock_js_api = MagicMock()
    mock_js_api.StreamConfig = MagicMock(return_value=MagicMock())
    mock_js_api.ConsumerConfig = MagicMock(return_value=MagicMock())
    mock_js_api.RetentionPolicy = MagicMock()
    mock_js_api.RetentionPolicy.WORK_QUEUE = "workqueue"
    mock_js_api.StorageType = MagicMock()
    mock_js_api.StorageType.FILE = "file"
    mock_js_api.DeliverPolicy = MagicMock()
    mock_js_api.DeliverPolicy.ALL = "all"
    mock_js_api.AckPolicy = MagicMock()
    mock_js_api.AckPolicy.EXPLICIT = "explicit"

    # BadRequestError must be a real Exception subclass for isinstance checks.
    class _BadRequestError(Exception):
        pass

    mock_js_errors = MagicMock()
    mock_js_errors.BadRequestError = _BadRequestError

    mock_nats.js = MagicMock()
    mock_nats.js.api = mock_js_api
    mock_nats.js.errors = mock_js_errors

    with (
        patch.dict(
            "sys.modules",
            {
                "nats": mock_nats,
                "nats.js": mock_nats.js,
                "nats.js.api": mock_js_api,
                "nats.js.errors": mock_js_errors,
                "nats.aio": MagicMock(),
                "nats.aio.client": MagicMock(),
            },
        ),
    ):
        yield mock_nats, mock_nc, mock_js, mock_js_api


@pytest.fixture
def adapter(mock_nats_module):
    """Return a NatsJetStreamEventBusAdapter with nats mocked out."""
    from hexastack_events.adapters.buses.nats import NatsJetStreamEventBusAdapter

    a = NatsJetStreamEventBusAdapter(
        servers=["nats://localhost:4222"],
        stream_name="hexastack",
        subject_prefix="hexastack.events",
    )
    return a, mock_nats_module


# ---------------------------------------------------------------------------
# Import guard tests
# ---------------------------------------------------------------------------


def test_import_error_without_nats():
    """Verify ImportError is raised with a helpful message when nats is absent."""
    with patch.dict("sys.modules", {"nats": None}):
        # Re-import to trigger the _require_nats() guard.
        import importlib

        nats_mod = importlib.import_module("hexastack_events.adapters.buses.nats")
        importlib.reload(nats_mod)

        with pytest.raises(ImportError, match="hexastack-events\\[nats\\]"):
            nats_mod._require_nats()


# ---------------------------------------------------------------------------
# Connection tests
# ---------------------------------------------------------------------------


def test_connect_establishes_nc_and_js(adapter):
    """Verify connect() calls nats.connect and configures JetStream."""
    a, (mock_nats, mock_nc, mock_js, _) = adapter

    a._run(a.connect())

    mock_nats.connect.assert_awaited_once_with(["nats://localhost:4222"])
    mock_nc.jetstream.assert_called_once()
    mock_js.add_stream.assert_awaited_once()


def test_connect_is_idempotent(adapter):
    """Verify a second connect() while already connected is a no-op."""
    a, (mock_nats, mock_nc, mock_js, _) = adapter

    a._run(a.connect())
    a._run(a.connect())

    assert mock_nats.connect.await_count == 1


def test_connect_failure_raises_event_delivery_error(mock_nats_module):
    """Verify EventDeliveryError is raised when NATS connection fails."""
    mock_nats, mock_nc, mock_js, _ = mock_nats_module
    mock_nats.connect = AsyncMock(side_effect=OSError("connection refused"))

    from hexastack_events.adapters.buses.nats import NatsJetStreamEventBusAdapter

    a = NatsJetStreamEventBusAdapter(servers=["nats://bad-host:4222"])

    with pytest.raises(EventDeliveryError, match="Failed to connect"):
        a._run(a.connect())


def test_connect_stream_already_exists_updates_stream(mock_nats_module):
    """Verify update_stream is called when add_stream raises BadRequestError."""
    mock_nats, mock_nc, mock_js, _ = mock_nats_module

    # Use the mocked BadRequestError registered in sys.modules by the fixture.
    import nats.js.errors as js_errors

    mock_js.add_stream = AsyncMock(side_effect=js_errors.BadRequestError())

    from hexastack_events.adapters.buses.nats import NatsJetStreamEventBusAdapter

    a = NatsJetStreamEventBusAdapter()
    a._run(a.connect())

    mock_js.update_stream.assert_awaited_once()


# ---------------------------------------------------------------------------
# publish_envelope tests
# ---------------------------------------------------------------------------


def test_publish_envelope_sends_correct_subject_and_payload(adapter):
    """Verify publish_envelope routes to the correct NATS subject with encoded bytes."""
    a, (_, _, mock_js, _) = adapter
    a._run(a.connect())

    envelope = _make_envelope("OrderCreatedEvent")
    a.publish_envelope(envelope)

    expected_subject = "hexastack.events.OrderCreatedEvent"
    expected_payload = encode_cloudevent_bytes(envelope)

    mock_js.publish.assert_awaited_once_with(expected_subject, expected_payload)


def test_publish_envelope_raises_when_disconnected(mock_nats_module):
    """Verify EventDeliveryError is raised if publish_envelope is called before connect."""
    from hexastack_events.adapters.buses.nats import NatsJetStreamEventBusAdapter

    a = NatsJetStreamEventBusAdapter()

    with pytest.raises(EventDeliveryError, match="not connected"):
        a.publish_envelope(_make_envelope())


def test_publish_envelope_raises_on_nats_failure(adapter):
    """Verify EventDeliveryError wraps NATS publish exceptions."""
    a, (_, _, mock_js, _) = adapter
    a._run(a.connect())
    mock_js.publish = AsyncMock(side_effect=RuntimeError("network error"))

    with pytest.raises(EventDeliveryError, match="NATS JetStream publish"):
        a.publish_envelope(_make_envelope())


# ---------------------------------------------------------------------------
# publish (domain event wrapping) tests
# ---------------------------------------------------------------------------


def test_publish_wraps_event_into_cloud_event_envelope(adapter):
    """Verify publish() builds a CloudEventEnvelope from a domain event and publishes it."""
    a, (_, _, mock_js, _) = adapter
    a._run(a.connect())

    event = OrderCreatedEvent(order_id="o-42", amount=199.0)
    a.publish(event)

    # Should have published to the OrderCreatedEvent subject.
    call_args = mock_js.publish.call_args
    assert call_args is not None
    subject = call_args[0][0]
    assert subject == "hexastack.events.OrderCreatedEvent"


# ---------------------------------------------------------------------------
# subscribe tests
# ---------------------------------------------------------------------------


def test_subscribe_sets_up_durable_consumer_with_correct_subject(adapter):
    """Verify subscribe creates a durable consumer on the correct subject."""
    a, (_, _, mock_js, _) = adapter
    a._run(a.connect())

    handler = MagicMock()
    a.subscribe("OrderCreatedEvent", handler)

    mock_js.subscribe.assert_awaited_once()
    call_kwargs = mock_js.subscribe.call_args
    assert call_kwargs[0][0] == "hexastack.events.OrderCreatedEvent"
    assert call_kwargs[1]["durable"] == "hexastack-OrderCreatedEvent"


def test_subscribe_raises_when_disconnected(mock_nats_module):
    """Verify EventDeliveryError when subscribe called before connect."""
    from hexastack_events.adapters.buses.nats import NatsJetStreamEventBusAdapter

    a = NatsJetStreamEventBusAdapter()

    with pytest.raises(EventDeliveryError, match="not connected"):
        a.subscribe("SomeEvent", lambda e: None)


def test_subscribe_raises_on_js_failure(adapter):
    """Verify EventDeliveryError wraps JetStream subscribe exceptions."""
    a, (_, _, mock_js, _) = adapter
    a._run(a.connect())
    mock_js.subscribe = AsyncMock(side_effect=RuntimeError("subscribe failed"))

    with pytest.raises(EventDeliveryError, match="Failed to subscribe"):
        a.subscribe("OrderCreatedEvent", lambda e: None)


# ---------------------------------------------------------------------------
# disconnect tests
# ---------------------------------------------------------------------------


def test_disconnect_drains_and_clears_state(adapter):
    """Verify disconnect drains the NATS connection and resets internal state."""
    a, (_, mock_nc, _, _) = adapter
    a._run(a.connect())

    assert a._nc is not None
    a._run(a.disconnect())

    mock_nc.drain.assert_awaited_once()
    assert a._nc is None
    assert a._js is None


# ---------------------------------------------------------------------------
# Async context manager tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_async_context_manager_connects_and_disconnects(mock_nats_module):
    """Verify __aenter__ connects and __aexit__ disconnects cleanly."""
    mock_nats, mock_nc, mock_js, _ = mock_nats_module

    from hexastack_events.adapters.buses.nats import NatsJetStreamEventBusAdapter

    a = NatsJetStreamEventBusAdapter()

    async with a:
        assert a._nc is not None

    mock_nc.drain.assert_awaited_once()
    assert a._nc is None
