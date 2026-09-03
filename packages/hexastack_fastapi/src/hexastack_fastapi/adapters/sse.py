"""Server-Sent Events (SSE) Streaming Response Adapters for FastAPI & Starlette."""

from __future__ import annotations

import asyncio
import contextlib
from collections.abc import AsyncIterable, AsyncIterator
from dataclasses import dataclass
from typing import Any

from fastapi.responses import Response
from starlette.background import BackgroundTask
from starlette.types import Receive, Scope, Send


@dataclass(frozen=True)
class ServerSentEvent:
    """Represents an individual Server-Sent Event frame.

    Notes/Architectural Intent:
        Standardizes the W3C Server-Sent Events wire format.
        Supports structured JSON data, event type naming, event IDs, retry intervals,
        and keep-alive comments.
    """

    data: Any = None
    event: str | None = None
    id: str | None = None
    retry: int | None = None
    comment: str | None = None

    def encode(self) -> bytes:
        """Encode the Server-Sent Event into bytes conforming to the text/event-stream spec.

        Returns:
            Encoded bytes terminated with double newlines.
        """
        buffer: list[str] = []

        if self.comment is not None:
            for line in self.comment.splitlines():
                buffer.append(f": {line}\n")

        if self.id is not None:
            buffer.append(f"id: {self.id}\n")

        if self.event is not None:
            buffer.append(f"event: {self.event}\n")

        if self.retry is not None:
            buffer.append(f"retry: {self.retry}\n")

        if self.data is not None:
            raw_data = str(self.data) if not isinstance(self.data, str) else self.data
            for line in raw_data.splitlines():
                buffer.append(f"data: {line}\n")
        elif self.comment is None and self.event is None and self.id is None:
            buffer.append("data:\n")

        buffer.append("\n")
        return "".join(buffer).encode("utf-8")


class EventSourceResponse(Response):
    """FastAPI/Starlette Response subclass streaming Server-Sent Events over HTTP.

    Notes/Architectural Intent:
        Implements chunked transfer encoding over HTTP/1.1 or standard HTTP/2/3 streams
        with media type 'text/event-stream'. Supports optional background ping keep-alives
        to prevent reverse proxy timeouts (e.g. NGINX, Cloudflare).
    """

    media_type = "text/event-stream"

    def __init__(
        self,
        content: AsyncIterable[ServerSentEvent | str | bytes | dict[str, Any]],
        status_code: int = 200,
        headers: dict[str, str] | None = None,
        media_type: str | None = None,
        background: BackgroundTask | None = None,
        ping_interval: float | None = None,
    ) -> None:
        """Initialize EventSourceResponse.

        Args:
            content: Async generator or iterable yielding ServerSentEvent or raw data.
            status_code: HTTP status code (default 200).
            headers: Optional HTTP headers dictionary.
            media_type: Content-Type override (defaults to text/event-stream).
            background: Optional Starlette BackgroundTask.
            ping_interval: Optional interval in seconds to yield keep-alive comment pings.
        """
        self.body_iterator = content
        self.ping_interval = ping_interval
        headers = headers or {}
        headers.setdefault("Cache-Control", "no-cache")
        headers.setdefault("Connection", "keep-alive")
        headers.setdefault("X-Accel-Buffering", "no")
        super().__init__(
            content=b"",
            status_code=status_code,
            headers=headers,
            media_type=media_type or self.media_type,
            background=background,
        )

    async def _stream_with_ping(self) -> AsyncIterator[bytes]:
        """Wrap body_iterator with periodic keep-alive pings."""
        queue: asyncio.Queue[bytes | None] = asyncio.Queue()

        async def _producer() -> None:
            try:
                async for item in self.body_iterator:
                    if isinstance(item, ServerSentEvent):
                        await queue.put(item.encode())
                    elif isinstance(item, bytes):
                        await queue.put(item)
                    elif isinstance(item, str):
                        await queue.put(ServerSentEvent(data=item).encode())
                    else:
                        import json

                        await queue.put(ServerSentEvent(data=json.dumps(item)).encode())
            except Exception:
                await queue.put(None)
                raise
            finally:
                await queue.put(None)

        producer_task = asyncio.create_task(_producer())

        try:
            while True:
                if self.ping_interval and self.ping_interval > 0:
                    try:
                        chunk = await asyncio.wait_for(
                            queue.get(), timeout=self.ping_interval
                        )
                        if chunk is None:
                            break
                        yield chunk
                    except TimeoutError:
                        yield ServerSentEvent(comment="ping").encode()
                else:
                    chunk = await queue.get()
                    if chunk is None:
                        break
                    yield chunk
        finally:
            if not producer_task.done():
                producer_task.cancel()
                with contextlib.suppress(asyncio.CancelledError, Exception):
                    _res = await producer_task

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        """ASGI response streaming callable."""
        await send(
            {
                "type": "http.response.start",
                "status": self.status_code,
                "headers": self.raw_headers,
            }
        )

        async for chunk in self._stream_with_ping():
            await send(
                {
                    "type": "http.response.body",
                    "body": chunk,
                    "more_body": True,
                }
            )

        await send(
            {
                "type": "http.response.body",
                "body": b"",
                "more_body": False,
            }
        )

        if self.background is not None:
            await self.background()


__all__ = [
    "EventSourceResponse",
    "ServerSentEvent",
]
