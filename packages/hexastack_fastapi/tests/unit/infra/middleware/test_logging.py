import pytest
from fastapi import FastAPI
from fastapi.responses import JSONResponse
from fastapi.testclient import TestClient
from rodi import Container

from hexastack_core.adapters.logging.in_memory import InMemoryLogger
from hexastack_core.ports.logging import LoggingPort
from hexastack_fastapi.infra.config import (
    HexastackFastApiConfig,
    RequestLoggingConfig,
)
from hexastack_fastapi.infra.middleware.logging import (
    RequestLoggingHttpMiddleware,
)


def _make_app(
    logger: InMemoryLogger | None = None,
    *,
    exclude_paths: list[str] | None = None,
    enable: bool = True,
) -> tuple[TestClient, InMemoryLogger]:
    log = logger or InMemoryLogger()
    container = Container()
    container.add_instance(log, declared_class=LoggingPort)
    cfg = HexastackFastApiConfig(
        logging=RequestLoggingConfig(
            enable=enable,
            exclude_paths=exclude_paths or [],
        )
    )
    app = FastAPI()
    app.add_middleware(RequestLoggingHttpMiddleware, config=cfg, container=container)

    @app.get("/items")
    async def get_items():
        return [{"id": 1}]

    @app.post("/items")
    async def create_item():
        return JSONResponse(status_code=201, content={"id": 2})

    @app.get("/health")
    async def health():
        return {"status": "ok"}

    @app.get("/client-err")
    async def client_err():
        return JSONResponse(status_code=404, content={"error": "Not Found"})

    @app.get("/server-err")
    async def server_err():
        return JSONResponse(status_code=500, content={"error": "Server Error"})

    return TestClient(app), log


def test_request_logging_middleware_2xx_is_info():
    client, logger = _make_app()
    client.get("/items")
    assert logger.entries[0].level.lower() == "info"
    assert logger.entries[0].extra is not None
    assert logger.entries[0].extra["client_ip"] == "testclient"
    assert "GET /items HTTP/1.1 -> 200" in logger.entries[0].message


def test_request_logging_middleware_4xx_is_warning():
    client, logger = _make_app()
    client.get("/client-err")
    assert logger.entries[0].level.lower() == "warning"
    assert logger.entries[0].extra is not None
    assert logger.entries[0].extra["http_status"] == 404
    assert "GET /client-err HTTP/1.1 -> 404" in logger.entries[0].message


def test_request_logging_middleware_5xx_is_error():
    client, logger = _make_app()
    client.get("/server-err")
    assert logger.entries[0].level.lower() == "error"
    assert logger.entries[0].extra is not None
    assert logger.entries[0].extra["http_status"] == 500
    assert "GET /server-err HTTP/1.1 -> 500" in logger.entries[0].message


def test_request_logging_middleware_disabled():
    client, logger = _make_app(enable=False)
    client.get("/items")
    assert len(logger.entries) == 0


def test_request_logging_middleware_post_method_and_status():
    client, logger = _make_app()
    client.post("/items")
    assert len(logger.entries) == 1
    assert logger.entries[0].extra is not None
    assert logger.entries[0].extra["http_method"] == "POST"
    assert logger.entries[0].extra["http_status"] == 201
    assert "POST /items HTTP/1.1 -> 201" in logger.entries[0].message


@pytest.mark.anyio
async def test_request_logging_middleware_direct_asgi_scope_handling():
    logger = InMemoryLogger()

    async def mock_lifespan_app(scope, receive, send):
        pass

    middleware = RequestLoggingHttpMiddleware(
        app=mock_lifespan_app,
        logger=logger,
    )

    async def dummy_receive():
        return {"type": "http.request"}

    async def dummy_send(m):
        pass

    # 1. Non-HTTP scope bypass
    await middleware({"type": "lifespan"}, dummy_receive, dummy_send)
    assert len(logger.entries) == 0

    # 2. HTTP scope with missing client (client_ip defaults to "unknown")
    async def mock_app(scope, receive, send):
        await send({"type": "http.response.start", "status": 200})
        await send({"type": "http.response.body", "body": b""})

    middleware._app = mock_app
    messages = []

    async def mock_send(m):
        messages.append(m)

    await middleware(
        {"type": "http", "path": "/api", "method": "GET", "http_version": "2.0"},
        dummy_receive,
        mock_send,
    )
    assert len(logger.entries) == 1
    assert logger.entries[0].extra is not None
    assert logger.entries[0].extra["client_ip"] == "unknown"
    assert logger.entries[0].extra["http_path"] == "/api"
    assert "GET /api HTTP/2.0 -> 200" in logger.entries[0].message
