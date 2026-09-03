"""Unit tests for ServerSentEvent and EventSourceResponse in hexastack_fastapi."""

from __future__ import annotations

import asyncio

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from hexastack_fastapi.adapters.sse import EventSourceResponse, ServerSentEvent


def test_server_sent_event_encode_minimal() -> None:
    """Verify standard data encoding."""
    event = ServerSentEvent(data="hello world")
    raw = event.encode()
    assert raw == b"data: hello world\n\n"


def test_server_sent_event_encode_multiline_data() -> None:
    """Verify multiline data is prefixed per line."""
    event = ServerSentEvent(data="line 1\nline 2")
    raw = event.encode()
    assert raw == b"data: line 1\ndata: line 2\n\n"


def test_server_sent_event_encode_full_fields() -> None:
    """Verify id, event, retry, comment, and data fields."""
    event = ServerSentEvent(
        id="evt-42",
        event="user_connected",
        retry=5000,
        comment="heartbeat ping",
        data="online",
    )
    raw = event.encode().decode("utf-8")
    assert ": heartbeat ping\n" in raw
    assert "id: evt-42\n" in raw
    assert "event: user_connected\n" in raw
    assert "retry: 5000\n" in raw
    assert "data: online\n" in raw
    assert raw.endswith("\n\n")


def test_server_sent_event_empty() -> None:
    """Verify empty event defaults to empty data line."""
    event = ServerSentEvent()
    raw = event.encode()
    assert raw == b"data:\n\n"


@pytest.mark.anyio
async def test_event_source_response_streaming_http() -> None:
    """Verify EventSourceResponse streams chunks with text/event-stream headers."""
    app = FastAPI()

    @app.get("/stream")
    async def sse_endpoint() -> EventSourceResponse:
        async def generator():
            yield ServerSentEvent(data="first", id="1")
            yield ServerSentEvent(data="second", id="2", event="update")
            yield {"key": "json_val"}

        return EventSourceResponse(generator())

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        response = await client.get("/stream")
        assert response.status_code == 200
        assert "text/event-stream" in response.headers["content-type"]
        assert response.headers["cache-control"] == "no-cache"
        assert response.headers["connection"] == "keep-alive"

        body = response.text
        assert "data: first\n" in body
        assert "id: 1\n" in body
        assert "event: update\n" in body
        assert "data: second\n" in body
        assert 'data: {"key": "json_val"}\n' in body


@pytest.mark.anyio
async def test_event_source_response_keep_alive_ping() -> None:
    """Verify EventSourceResponse sends periodic keep-alive comments."""
    app = FastAPI()

    @app.get("/slow-stream")
    async def slow_endpoint() -> EventSourceResponse:
        async def slow_gen():
            yield ServerSentEvent(data="start")
            await asyncio.sleep(0.08)
            yield ServerSentEvent(data="end")

        return EventSourceResponse(slow_gen(), ping_interval=0.03)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        response = await client.get("/slow-stream")
        assert response.status_code == 200
        body = response.text
        assert ": ping\n\n" in body
        assert "data: start\n\n" in body
        assert "data: end\n\n" in body
