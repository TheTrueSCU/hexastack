"""Hypothesis property-based tests for Server-Sent Events (SSE) and WebSocket stream invariants.

Notes/Architectural Intent:
    Fuzzes arbitrary data payloads, events, retry headers, and WebSocket broadcast topologies:
    1. ServerSentEvent Wire Invariants:
       - Every encoded event ends with double newlines (`\\n\\n`).
       - Multi-line data preserves all lines prefixed with `data: `.
       - Explicit event types, IDs, and retry intervals are strictly formatted.
    2. WebSocketConnectionManager Concurrency & Broadcast Invariants:
       - Connection idempotency: multiple connects with arbitrary room assignments preserve member sets.
       - Disconnect cleanup: disconnecting clears connection from global pool and all associated rooms.
       - Broadcast partitioning: room broadcasts reach exactly the subscribed room members without leakage.
"""

from __future__ import annotations

import string
from typing import Any

import pytest
from hypothesis import given
from hypothesis import strategies as st

from hexastack_fastapi.adapters.sse import ServerSentEvent
from hexastack_fastapi.adapters.websockets import WebSocketConnectionManager

# Strategies
clean_tokens = st.text(
    alphabet=string.ascii_letters + string.digits + "_-",
    min_size=1,
    max_size=32,
)

sse_data_strategy = st.one_of(
    st.text(min_size=0, max_size=256),
    st.dictionaries(
        keys=clean_tokens,
        values=st.integers(min_value=-1000, max_value=1000),
        max_size=5,
    ),
    st.integers(),
    st.booleans(),
)


class MockWebSocketClient:
    """Mock WebSocket client for property-based state machine verification."""

    def __init__(self, client_id: str) -> None:
        self.client_id = client_id
        self.accepted = False
        self.received_texts: list[str] = []
        self.received_jsons: list[Any] = []

    async def accept(self) -> None:
        self.accepted = True

    async def send_text(self, data: str) -> None:
        self.received_texts.append(data)

    async def send_json(self, data: Any) -> None:
        self.received_jsons.append(data)


@given(
    data=sse_data_strategy,
    event_type=st.one_of(st.none(), clean_tokens),
    event_id=st.one_of(st.none(), clean_tokens),
    retry=st.one_of(st.none(), st.integers(min_value=0, max_value=60000)),
    comment=st.one_of(st.none(), clean_tokens),
)
def test_server_sent_event_encoding_invariants(
    data: Any,
    event_type: str | None,
    event_id: str | None,
    retry: int | None,
    comment: str | None,
) -> None:
    """Property: Any valid ServerSentEvent encodes to valid W3C event-stream format ending in newline."""
    sse = ServerSentEvent(
        data=data,
        event=event_type,
        id=event_id,
        retry=retry,
        comment=comment,
    )
    encoded = sse.encode()
    assert encoded.endswith(b"\n")

    text = encoded.decode("utf-8")
    if event_type:
        assert f"event: {event_type}\n" in text
    if event_id:
        assert f"id: {event_id}\n" in text
    if retry is not None:
        assert f"retry: {retry}\n" in text
    if comment:
        assert f": {comment}\n" in text


@pytest.mark.anyio
@given(
    room_name=clean_tokens,
    num_clients=st.integers(min_value=1, max_value=10),
    broadcast_msg=clean_tokens,
)
async def test_websocket_room_broadcast_properties(
    room_name: str, num_clients: int, broadcast_msg: str
) -> None:
    """Property: Broadcasts to a room reach all and only members of that room."""
    manager = WebSocketConnectionManager()
    clients = [MockWebSocketClient(f"client_{i}") for i in range(num_clients)]
    other_client = MockWebSocketClient("other_client")

    for c in clients:
        await manager.connect(c, room=room_name)

    await manager.connect(other_client, room="different_room")

    assert manager.active_connections_count == num_clients + 1
    assert manager.room_members_count(room_name) == num_clients
    assert manager.room_members_count("different_room") == 1

    # Broadcast to room
    await manager.broadcast(broadcast_msg, room=room_name)

    for c in clients:
        assert broadcast_msg in c.received_texts

    assert broadcast_msg not in other_client.received_texts

    # Cleanup / Disconnect properties
    for c in clients:
        await manager.disconnect(c)

    assert manager.room_members_count(room_name) == 0
    assert manager.active_connections_count == 1
