import pytest
from fastapi import FastAPI
from fastapi.responses import JSONResponse
from fastapi.testclient import TestClient
from inline_snapshot import snapshot
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


@pytest.mark.snapshot
def test_request_logging_middleware_success():
    logger = InMemoryLogger()
    container = Container()
    container.add_instance(logger, declared_class=LoggingPort)

    cfg = HexastackFastApiConfig(
        logging=RequestLoggingConfig(
            enable=True,
            exclude_paths=["/health"],
        )
    )

    app = FastAPI()
    app.add_middleware(
        RequestLoggingHttpMiddleware,
        config=cfg,
        container=container,
    )

    @app.get("/items")
    async def get_items():
        return [{"id": 1}]

    @app.get("/health")
    async def health():
        return {"status": "ok"}

    client = TestClient(app)

    res = client.get("/items")
    assert res.status_code == 200
    assert len(logger.entries) == 1
    entry = logger.entries[0]

    assert {
        "level": entry.level,
        "message_contains": "GET /items HTTP/1.1 -> 200" in entry.message,
        "http_status": entry.extra["http_status"] if entry.extra else None,
        "has_duration_ms": "duration_ms" in (entry.extra or {}),
    } == snapshot(
        {
            "level": "info",
            "message_contains": True,
            "http_status": 200,
            "has_duration_ms": True,
        }
    )  # duration_ms is dynamic — tested via has_duration_ms flag

    # Excluded path generates no log
    client.get("/health")
    assert len(logger.entries) == 1


@pytest.mark.snapshot
def test_request_logging_middleware_error_status():
    logger = InMemoryLogger()
    container = Container()
    container.add_instance(logger, declared_class=LoggingPort)

    app = FastAPI()
    app.add_middleware(
        RequestLoggingHttpMiddleware,
        container=container,
    )

    @app.get("/client-err")
    async def client_err():
        return JSONResponse(status_code=404, content={"error": "Not Found"})

    @app.get("/server-err")
    async def server_err():
        return JSONResponse(status_code=500, content={"error": "Server Error"})

    client = TestClient(app)

    client.get("/client-err")
    client.get("/server-err")

    assert [{"level": e.level} for e in logger.entries] == snapshot(
        [{"level": "warning"}, {"level": "error"}]
    )
