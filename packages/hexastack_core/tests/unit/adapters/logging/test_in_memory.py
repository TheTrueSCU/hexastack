import pytest
from inline_snapshot import snapshot

from hexastack_core.adapters.logging import InMemoryLogger


@pytest.mark.snapshot
def test_in_memory_logger_capture_and_filter():
    logger = InMemoryLogger()
    logger.info("Service boot", extra={"env": "test"})
    logger.debug("Debugging query", extra={"query_id": "q1"})
    logger.warning("Low memory warning")
    logger.error("DB connection dropped", exc=RuntimeError("disconnected"))

    entries = logger.all()

    assert [
        {
            "level": e.level,
            "message": e.message,
            "extra": e.extra,
            "exc": type(e.exc).__name__ if e.exc else None,
        }
        for e in entries
    ] == snapshot(
        [
            {
                "level": "info",
                "message": "Service boot",
                "extra": {"env": "test"},
                "exc": None,
            },
            {
                "level": "debug",
                "message": "Debugging query",
                "extra": {"query_id": "q1"},
                "exc": None,
            },
            {
                "level": "warning",
                "message": "Low memory warning",
                "extra": None,
                "exc": None,
            },
            {
                "level": "error",
                "message": "DB connection dropped",
                "extra": None,
                "exc": "RuntimeError",
            },
        ]
    )

    # Filter by level
    errors = logger.entries_by_level("error")
    assert len(errors) == 1
    assert errors[0].message == "DB connection dropped"

    # Clear
    logger.clear()
    assert len(logger.all()) == 0
