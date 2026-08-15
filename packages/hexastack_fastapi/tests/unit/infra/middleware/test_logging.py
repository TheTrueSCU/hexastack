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


def _make_app(
    logger: InMemoryLogger,
    *,
    exclude_paths: list[str] | None = None,
    enable: bool = True,
) -> TestClient:
    container = Container()
    container.add_instance(logger, declared_class=LoggingPort)
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

    @app.get("/health")
    async def health():
        return {"status": "ok"}

    @app.get("/client-err")
    async def client_err():
        return JSONResponse(status_code=404, content={"error": "Not Found"})

    @app.get("/server-err")
    async def server_err():
        return JSONResponse(status_code=500, content={"error": "Server Error"})

    return TestClient(app)


# ---------------------------------------------------------------------------
# extra dict field assertions (kills http_status, duration_ms, client_ip mutants)
# ---------------------------------------------------------------------------


@pytest.mark.snapshot
def test_request_logging_middleware_extra_fields():
    """Kills mutants for http_status, http_method, http_path, duration_ms, client_ip
    field assignments in the extra dict (lines 79–84)."""
    logger = InMemoryLogger()
    client = _make_app(logger)

    res = client.get("/items")
    assert res.status_code == 200
    assert len(logger.entries) == 1
    entry = logger.entries[0]

    assert entry.extra is not None
    # Explicit field kills — each assertion targets a specific mutant
    assert entry.extra["http_status"] == 200
    assert entry.extra["http_method"] == "GET"
    assert entry.extra["http_path"] == "/items"
    assert isinstance(entry.extra["duration_ms"], float)
    assert entry.extra["duration_ms"] >= 0
    assert "client_ip" in entry.extra

    # Message format assertion (kills line 77 mutant)
    assert "GET /items HTTP/1.1 -> 200" in entry.message

    # Static fields snapshot (duration_ms excluded — dynamic)
    assert {
        "level": entry.level,
        "message_contains": "GET /items HTTP/1.1 -> 200" in entry.message,
        "http_status": entry.extra["http_status"],
        "has_duration_ms": "duration_ms" in entry.extra,
    } == snapshot(
        {
            "level": "info",
            "message_contains": True,
            "http_status": 200,
            "has_duration_ms": True,
        }
    )  # duration_ms is dynamic — tested via has_duration_ms flag


# ---------------------------------------------------------------------------
# Log level branches: info (2xx), warning (4xx), error (5xx) (kills lines 85–90)
# ---------------------------------------------------------------------------


@pytest.mark.snapshot
def test_request_logging_middleware_log_levels():
    """Kills mutants for the status_code >= 500 / >= 400 / else branches."""
    logger = InMemoryLogger()
    client = _make_app(logger)

    client.get("/items")  # 200 → info
    client.get("/client-err")  # 404 → warning
    client.get("/server-err")  # 500 → error

    assert [
        {"level": e.level, "http_status": (e.extra or {})["http_status"]}
        for e in logger.entries
    ] == snapshot(
        [
            {"level": "info", "http_status": 200},
            {"level": "warning", "http_status": 404},
            {"level": "error", "http_status": 500},
        ]
    )


def test_request_logging_middleware_2xx_is_info():
    logger = InMemoryLogger()
    _make_app(logger).get("/items")
    assert logger.entries[0].level.lower() == "info"


def test_request_logging_middleware_4xx_is_warning():
    logger = InMemoryLogger()
    _make_app(logger).get("/client-err")
    assert logger.entries[0].level.lower() == "warning"
    assert logger.entries[0].extra is not None
    assert logger.entries[0].extra["http_status"] == 404


def test_request_logging_middleware_5xx_is_error():
    logger = InMemoryLogger()
    _make_app(logger).get("/server-err")
    assert logger.entries[0].level.lower() == "error"
    assert logger.entries[0].extra is not None
    assert logger.entries[0].extra["http_status"] == 500


# ---------------------------------------------------------------------------
# Exclude paths — no log emitted (kills path exclusion mutants)
# ---------------------------------------------------------------------------


@pytest.mark.snapshot
def test_request_logging_middleware_success():
    """Original snapshot test — exclude path produces no log entry."""
    logger = InMemoryLogger()
    client = _make_app(logger, exclude_paths=["/health"])

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
    client = _make_app(logger)

    client.get("/client-err")
    client.get("/server-err")

    assert [{"level": e.level} for e in logger.entries] == snapshot(
        [{"level": "warning"}, {"level": "error"}]
    )
