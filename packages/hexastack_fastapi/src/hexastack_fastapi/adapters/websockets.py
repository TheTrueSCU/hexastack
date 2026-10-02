"""WebSocket Connection Manager and Channel Router Adapters for FastAPI."""

from __future__ import annotations

import asyncio
import json
from collections import defaultdict
from collections.abc import Callable
from typing import Any

from fastapi import WebSocket, WebSocketDisconnect

from hexastack_core.domain import Command, Query
from hexastack_cqrs.infra.pipeline import ExecutionPipeline


class WebSocketConnectionManager:
    """Manages active WebSocket connections, grouping by room and client identity.

    Notes/Architectural Intent:
        Encapsulates connection lifecycle (connect, disconnect, broadcast) and room grouping.
        Maintains an in-memory connection registry protected by asyncio concurrency semantics.
    """

    def __init__(self) -> None:
        """Initialize WebSocketConnectionManager with empty connection pools."""
        self._active_connections: set[Any] = set()
        self._rooms: dict[str, set[Any]] = defaultdict(set)
        self._lock = asyncio.Lock()

    async def connect(self, websocket: Any, room: str | None = None) -> None:
        """Accept an incoming WebSocket connection and register in pools.

        Args:
            websocket: Incoming FastAPI WebSocket instance or mock.
            room: Optional room/channel identifier to subscribe to.
        """
        await websocket.accept()
        async with self._lock:
            self._active_connections.add(websocket)
            if room:
                self._rooms[room].add(websocket)

    async def disconnect(self, websocket: Any, room: str | None = None) -> None:
        """Remove a WebSocket connection from active pools and rooms.

        Args:
            websocket: Terminated WebSocket instance.
            room: Optional specific room from which to unsubscribe.
        """
        async with self._lock:
            self._active_connections.discard(websocket)
            if room and room in self._rooms:
                self._rooms[room].discard(websocket)
                if not self._rooms[room]:
                    del self._rooms[room]
            else:
                for r_name, members in list(self._rooms.items()):
                    members.discard(websocket)
                    if not members:
                        del self._rooms[r_name]

    async def send_personal_message(self, message: Any, websocket: Any) -> None:
        """Send a message directly to a single connected WebSocket client.

        Args:
            message: Text, dict, or JSON-serializable payload.
            websocket: Target WebSocket connection.
        """
        if isinstance(message, str):
            await websocket.send_text(message)
        elif isinstance(message, bytes):
            await websocket.send_bytes(message)
        else:
            await websocket.send_json(message)

    async def broadcast(self, message: Any, room: str | None = None) -> None:
        """Broadcast a message to all connected clients or a specific room.

        Args:
            message: Text, dict, or JSON-serializable payload.
            room: Optional room identifier. If None, broadcasts to all active connections.
        """
        async with self._lock:
            targets = list(
                self._rooms.get(room, set()) if room else self._active_connections
            )

        for connection in targets:
            try:
                if isinstance(message, str):
                    await connection.send_text(message)
                elif isinstance(message, bytes):
                    await connection.send_bytes(message)
                else:
                    await connection.send_json(message)
            except Exception:
                await self.disconnect(connection, room)

    @property
    def active_connections_count(self) -> int:
        """Return total count of active WebSocket connections."""
        return len(self._active_connections)

    def room_members_count(self, room: str) -> int:
        """Return count of active connections in a specific room."""
        return len(self._rooms.get(room, set()))


class WebSocketCqrsBridge:
    """Dispatches inbound WebSocket JSON payloads into CQRS ExecutionPipeline.

    Notes/Architectural Intent:
        Bridges real-time bidirectional WebSocket sessions to domain Commands and Queries,
        returning execution results over the socket.
    """

    def __init__(
        self,
        pipeline: ExecutionPipeline,
        manager: WebSocketConnectionManager | None = None,
    ) -> None:
        """Initialize WebSocketCqrsBridge.

        Args:
            pipeline: CQRS ExecutionPipeline instance.
            manager: Optional WebSocketConnectionManager instance.
        """
        self.pipeline = pipeline
        self.manager = manager or WebSocketConnectionManager()
        self._message_types: dict[str, type[Command | Query]] = {}

    def register_type(self, type_name: str, message_cls: type[Command | Query]) -> None:
        """Register a mapping from message type tag to Command/Query model.

        Args:
            type_name: String discriminator (e.g. 'CreateTask', 'GetStatus').
            message_cls: Model class to instantiate from payload.
        """
        self._message_types[type_name] = message_cls

    async def handle_connection(
        self,
        websocket: WebSocket,
        room: str | None = None,
        on_message: Callable[[Any], Any] | None = None,
    ) -> None:
        """Manage the lifecycle of a WebSocket connection dispatching CQRS messages.

        Args:
            websocket: Connected WebSocket.
            room: Optional room to join.
            on_message: Optional custom callback invoked per processed message.
        """
        await self.manager.connect(websocket, room=room)
        try:
            while True:
                data = await websocket.receive_text()
                try:
                    payload = json.loads(data)
                except json.JSONDecodeError:
                    await websocket.send_json(
                        {"status": "error", "error": "Invalid JSON payload"}
                    )
                    continue

                type_tag = payload.get("type")
                if not type_tag or type_tag not in self._message_types:
                    await websocket.send_json(
                        {
                            "status": "error",
                            "error": f"Unknown message type: {type_tag}",
                        }
                    )
                    continue

                msg_cls = self._message_types[type_tag]
                params = payload.get("payload", {})
                try:
                    instance = msg_cls(**params)
                    result = self.pipeline.execute(instance)
                    if asyncio.iscoroutine(result):
                        result = await result

                    response = {
                        "status": "ok",
                        "type": type_tag,
                        "data": result
                        if isinstance(result, (dict, list, str, int, float, bool))
                        else str(result),
                    }
                    await websocket.send_json(response)
                    if on_message:
                        cb_res = on_message(result)
                        if asyncio.iscoroutine(cb_res):
                            await cb_res
                except Exception as exc:
                    await websocket.send_json(
                        {
                            "status": "error",
                            "type": type_tag,
                            "error": str(exc),
                        }
                    )
        except WebSocketDisconnect:
            await self.manager.disconnect(websocket, room=room)


__all__ = [
    "WebSocketConnectionManager",
    "WebSocketCqrsBridge",
]
