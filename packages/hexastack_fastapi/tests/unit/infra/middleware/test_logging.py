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

    # 1. Access non-excluded path
    res = client.get("/items")
    assert res.status_code == 200
    assert len(logger.entries) == 1
    entry = logger.entries[0]
    assert entry.level.lower() == "info"
    assert "GET /items HTTP/1.1 -> 200" in entry.message
    assert entry.extra is not None
    assert entry.extra["http_status"] == 200
    assert "duration_ms" in entry.extra

    # 2. Access excluded path
    client.get("/health")
    # Still only 1 log entry
    assert len(logger.entries) == 1


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
    assert len(logger.entries) == 1
    assert logger.entries[0].level.lower() == "warning"

    client.get("/server-err")
    assert len(logger.entries) == 2
    assert logger.entries[1].level.lower() == "error"
