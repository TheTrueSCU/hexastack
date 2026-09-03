"""Unit tests for WebSocketConnectionManager and WebSocketCqrsBridge in hexastack_fastapi."""

from __future__ import annotations

import pytest
from fastapi import FastAPI, WebSocket
from fastapi.testclient import TestClient

from hexastack_core.domain import Command, Query
from hexastack_cqrs.adapters.buses.command.synchronous import SynchronousCommandBus
from hexastack_cqrs.adapters.buses.event.synchronous import SynchronousEventBus
from hexastack_cqrs.adapters.buses.query.synchronous import SynchronousQueryBus
from hexastack_cqrs.infra.pipeline import ExecutionPipeline
from hexastack_cqrs.infra.registries.command import CommandRegistry
from hexastack_cqrs.infra.registries.handler import HandlerRegistry
from hexastack_cqrs.infra.registries.presenter import PresenterRegistry
from hexastack_cqrs.infra.registries.query import QueryRegistry
from hexastack_fastapi.adapters.websockets import (
    WebSocketConnectionManager,
    WebSocketCqrsBridge,
)


class PingCommand(Command):
    message: str


class EchoQuery(Query):
    text: str


@pytest.mark.anyio
async def test_websocket_connection_manager_broadcast_and_rooms() -> None:
    """Verify WebSocketConnectionManager manages rooms and active count."""
    manager = WebSocketConnectionManager()
    assert manager.active_connections_count == 0

    class MockWebSocket:
        def __init__(self):
            self.accepted = False
            self.sent_texts: list[str] = []
            self.sent_jsons: list[dict] = []

        async def accept(self):
            self.accepted = True

        async def send_text(self, text: str):
            self.sent_texts.append(text)

        async def send_json(self, data: dict):
            self.sent_jsons.append(data)

    ws1 = MockWebSocket()
    ws2 = MockWebSocket()

    await manager.connect(ws1, room="general")  # type: ignore[arg-type]
    await manager.connect(ws2, room="alerts")  # type: ignore[arg-type]

    assert manager.active_connections_count == 2
    assert manager.room_members_count("general") == 1
    assert manager.room_members_count("alerts") == 1
    assert manager.room_members_count("empty") == 0

    # Broadcast to room
    await manager.broadcast("hello general", room="general")
    assert ws1.sent_texts == ["hello general"]
    assert ws2.sent_texts == []

    # Broadcast global
    await manager.broadcast({"type": "global_notice"})
    assert ws1.sent_jsons == [{"type": "global_notice"}]
    assert ws2.sent_jsons == [{"type": "global_notice"}]

    # Disconnect
    await manager.disconnect(ws1, room="general")  # type: ignore[arg-type]
    assert manager.active_connections_count == 1
    assert manager.room_members_count("general") == 0


def test_websocket_cqrs_bridge_dispatch() -> None:
    """Verify WebSocketCqrsBridge accepts socket connection and dispatches CQRS messages."""
    handler_reg = HandlerRegistry()
    handler_reg.register(PingCommand, lambda c: f"pong: {c.message}")
    handler_reg.register(EchoQuery, lambda q: f"echo: {q.text}")

    pipeline = ExecutionPipeline(
        command_bus=SynchronousCommandBus(handler_registry=handler_reg),
        query_bus=SynchronousQueryBus(handler_registry=handler_reg),
        event_bus=SynchronousEventBus(),
        command_registry=CommandRegistry(),
        query_registry=QueryRegistry(),
        handler_registry=handler_reg,
        presenter_registry=PresenterRegistry(),
    )

    bridge = WebSocketCqrsBridge(pipeline=pipeline)
    bridge.register_type("Ping", PingCommand)
    bridge.register_type("Echo", EchoQuery)

    app = FastAPI()

    @app.websocket("/ws")
    async def ws_endpoint(websocket: WebSocket) -> None:
        await bridge.handle_connection(websocket, room="test_room")

    client = TestClient(app)
    with client.websocket_connect("/ws") as websocket:
        # 1. Invalid JSON
        websocket.send_text("not json")
        res_err = websocket.receive_json()
        assert res_err["status"] == "error"
        assert "Invalid JSON" in res_err["error"]

        # 2. Unknown Type
        websocket.send_json({"type": "UnknownAction"})
        res_unk = websocket.receive_json()
        assert res_unk["status"] == "error"
        assert "Unknown message type" in res_unk["error"]

        # 3. Valid Command Execution
        websocket.send_json({"type": "Ping", "payload": {"message": "live check"}})
        res_cmd = websocket.receive_json()
        assert res_cmd["status"] == "ok"
        assert res_cmd["data"] == "pong: live check"

        # 4. Valid Query Execution
        websocket.send_json({"type": "Echo", "payload": {"text": "realtime"}})
        res_qry = websocket.receive_json()
        assert res_qry["status"] == "ok"
        assert res_qry["data"] == "echo: realtime"
