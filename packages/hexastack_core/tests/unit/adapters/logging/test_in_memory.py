from hexastack_core.adapters.logging import InMemoryLogger


def test_in_memory_logger_capture_and_filter():
    logger = InMemoryLogger()
    logger.info("Service boot", extra={"env": "test"})
    logger.debug("Debugging query", extra={"query_id": "q1"})
    logger.warning("Low memory warning")
    logger.error("DB connection dropped", exc=RuntimeError("disconnected"))

    entries = logger.all()
    assert len(entries) == 4

    assert entries[0].level == "info"
    assert entries[0].message == "Service boot"
    assert entries[0].extra == {"env": "test"}

    assert entries[1].level == "debug"
    assert entries[1].message == "Debugging query"

    assert entries[2].level == "warning"
    assert entries[2].message == "Low memory warning"

    assert entries[3].level == "error"
    assert entries[3].message == "DB connection dropped"
    assert isinstance(entries[3].exc, RuntimeError)

    # Filter by level
    errors = logger.entries_by_level("error")
    assert len(errors) == 1
    assert errors[0].message == "DB connection dropped"

    # Clear
    logger.clear()
    assert len(logger.all()) == 0
