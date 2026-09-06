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
    assert errors[0].level == "error"
    assert errors[0].message == "DB connection dropped"
    assert errors[0].extra is None
    assert isinstance(errors[0].exc, RuntimeError)

    warnings = logger.entries_by_level("warning")
    assert len(warnings) == 1
    assert warnings[0].level == "warning"
    assert warnings[0].message == "Low memory warning"

    # Warning and Error with explicit extra
    logger.warning("High CPU", extra={"usage": "99%"})
    logger.error("Out of memory", extra={"heap": "100%"}, exc=MemoryError("OOM"))
    latest_warn = logger.entries_by_level("warning")[-1]
    assert latest_warn.level == "warning"
    assert latest_warn.extra == {"usage": "99%"}
    latest_err = logger.entries_by_level("error")[-1]
    assert latest_err.level == "error"
    assert latest_err.extra == {"heap": "100%"}
    assert isinstance(latest_err.exc, MemoryError)

    # Clear
    logger.clear()
    assert len(logger.all()) == 0
