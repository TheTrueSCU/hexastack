"""Unit tests for JanusEventChannel and JanusCommandQueue.

Notes/Architectural Intent:
    Tests validate the sync-to-async and async-to-async handoff semantics of
    the janus bridge. A real janus.Queue is used (janus is a pure-Python package
    with no external dependencies), but tests are entirely in-process with no
    NATS server or thread contention.
"""

from __future__ import annotations

import asyncio
import contextlib
import threading
from dataclasses import dataclass
from typing import cast
from unittest.mock import patch

import pytest

from hexastack_events.domain.models import CloudEventEnvelope

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_envelope(event_type: str = "TestEvent") -> CloudEventEnvelope:
    """Build a minimal CloudEventEnvelope for bridge tests."""
    return CloudEventEnvelope(
        id="bridge-test-1",
        source="hexastack.events",
        type=event_type,
        time="2026-08-31T00:00:00+00:00",
        data={"key": "value"},
    )


@dataclass
class DummyCommand:
    """Minimal command dataclass for JanusCommandQueue generic tests."""

    action: str
    value: int


# ---------------------------------------------------------------------------
# Import guard tests
# ---------------------------------------------------------------------------


def test_import_error_without_janus():
    """Verify ImportError is raised with a helpful message when janus is absent."""
    with patch.dict("sys.modules", {"janus": None}):
        import importlib

        janus_mod = importlib.import_module(
            "hexastack_events.adapters.buses.janus_bridge"
        )
        importlib.reload(janus_mod)

        with pytest.raises(ImportError, match="hexastack-events\\[janus\\]"):
            janus_mod._require_janus()


# ---------------------------------------------------------------------------
# JanusEventChannel tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_janus_event_channel_async_put_and_async_get():
    """Verify async_put → async_get round-trip within the same event loop."""
    from hexastack_events.adapters.buses.janus_bridge import JanusEventChannel

    channel = JanusEventChannel()
    envelope = _make_envelope("OrderShipped")

    await channel.async_put(envelope)
    result = cast("CloudEventEnvelope", await channel.async_get())

    assert result.id == envelope.id
    assert result.type == "OrderShipped"

    channel.close()


@pytest.mark.asyncio
async def test_janus_event_channel_sync_put_async_get():
    """Verify sync_put from a worker thread is retrievable via async_get."""
    from hexastack_events.adapters.buses.janus_bridge import JanusEventChannel

    channel = JanusEventChannel()
    envelope = _make_envelope("PaymentReceived")

    def _sync_producer():
        channel.sync_put(envelope)

    # sync_put from a background thread
    t = threading.Thread(target=_sync_producer)
    t.start()
    t.join(timeout=2.0)

    result = cast(
        "CloudEventEnvelope",
        await asyncio.wait_for(channel.async_get(), timeout=2.0),
    )

    assert result.type == "PaymentReceived"
    channel.close()


@pytest.mark.asyncio
async def test_janus_event_channel_drain_processes_all_items():
    """Verify drain() calls the handler for every enqueued item."""
    from hexastack_events.adapters.buses.janus_bridge import JanusEventChannel

    channel = JanusEventChannel()
    received: list[CloudEventEnvelope] = []

    envelopes = [_make_envelope(f"Event{i}") for i in range(5)]
    for env in envelopes:
        channel.sync_put(env)

    async def handler(item: CloudEventEnvelope) -> None:
        received.append(item)
        if len(received) == len(envelopes):
            drain_task.cancel()

    drain_task = asyncio.create_task(channel.drain(handler))

    with contextlib.suppress(TimeoutError, asyncio.CancelledError):
        await asyncio.wait_for(drain_task, timeout=3.0)

    assert len(received) == 5
    assert [e.type for e in received] == [f"Event{i}" for i in range(5)]

    channel.close()


@pytest.mark.asyncio
async def test_janus_event_channel_drain_respects_cancellation():
    """Verify drain() exits cleanly when its task is cancelled."""
    from hexastack_events.adapters.buses.janus_bridge import JanusEventChannel

    channel = JanusEventChannel()
    handler_calls: list[int] = []

    async def handler(_: CloudEventEnvelope) -> None:
        handler_calls.append(1)

    drain_task = asyncio.create_task(channel.drain(handler))
    await asyncio.sleep(0.01)
    _ = drain_task.cancel()

    with contextlib.suppress(asyncio.CancelledError):
        await drain_task

    # Task must be done (cancelled or finished), not still running.
    assert drain_task.done()
    channel.close()


@pytest.mark.asyncio
async def test_janus_event_channel_maxsize_blocks_sync_put():
    """Verify sync_put blocks the caller when the queue is at maxsize."""
    from hexastack_events.adapters.buses.janus_bridge import JanusEventChannel

    channel = JanusEventChannel(maxsize=1)
    channel.sync_put(_make_envelope("First"))

    # A second sync_put to a full queue should block.
    # We run it in a thread with a timeout to detect the block.
    results: list[bool] = []

    def try_put():
        try:
            # Use the underlying sync queue with a timeout to avoid hanging tests.
            channel._queue.sync_q.put(_make_envelope("Second"), timeout=0.1)
            results.append(True)
        except Exception:
            results.append(False)

    t = threading.Thread(target=try_put)
    t.start()
    t.join(timeout=1.0)

    # Should have timed out (False) because queue is full.
    assert results == [False]
    channel.close()


# ---------------------------------------------------------------------------
# JanusCommandQueue tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_janus_command_queue_sync_put_async_get_round_trip():
    """Verify JanusCommandQueue[T] sync_put → async_get round-trip."""
    from hexastack_events.adapters.buses.janus_bridge import JanusCommandQueue

    queue: JanusCommandQueue[DummyCommand] = JanusCommandQueue()
    cmd = DummyCommand(action="process", value=42)

    def _producer():
        queue.sync_put(cmd)

    t = threading.Thread(target=_producer)
    t.start()
    t.join(timeout=2.0)

    result = await asyncio.wait_for(queue.async_get(), timeout=2.0)

    assert result.action == "process"
    assert result.value == 42

    queue.close()


@pytest.mark.asyncio
async def test_janus_command_queue_drain_dispatches_commands():
    """Verify JanusCommandQueue.drain() dispatches each command to the handler."""
    from hexastack_events.adapters.buses.janus_bridge import JanusCommandQueue

    queue: JanusCommandQueue[DummyCommand] = JanusCommandQueue()
    dispatched: list[DummyCommand] = []
    commands = [DummyCommand(action=f"cmd-{i}", value=i) for i in range(3)]

    for cmd in commands:
        queue.sync_put(cmd)

    async def dispatch(cmd: DummyCommand) -> None:
        dispatched.append(cmd)
        if len(dispatched) == len(commands):
            drain_task.cancel()

    drain_task = asyncio.create_task(queue.drain(dispatch))

    with contextlib.suppress(TimeoutError, asyncio.CancelledError):
        await asyncio.wait_for(drain_task, timeout=3.0)

    assert len(dispatched) == 3
    assert dispatched[0].action == "cmd-0"
    assert dispatched[2].value == 2

    queue.close()


@pytest.mark.asyncio
async def test_janus_command_queue_drain_cancels_cleanly():
    """Verify JanusCommandQueue.drain() task cancels without errors."""
    from hexastack_events.adapters.buses.janus_bridge import JanusCommandQueue

    queue: JanusCommandQueue[DummyCommand] = JanusCommandQueue()

    async def dispatch(_: DummyCommand) -> None:
        pass

    task = asyncio.create_task(queue.drain(dispatch))
    await asyncio.sleep(0.01)
    _ = task.cancel()

    with contextlib.suppress(asyncio.CancelledError):
        await task

    assert task.done()
    queue.close()
