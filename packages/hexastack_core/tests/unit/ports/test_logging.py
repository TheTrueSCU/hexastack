from hexastack_core.adapters.logging import InMemoryLogger
from hexastack_core.ports.logging import LoggingPort


def test_logging_port_contract(in_memory_logger: InMemoryLogger):
    logger: LoggingPort = in_memory_logger
    logger.info("Service started", extra={"port": 8080})
    logger.error("Database connection failed", exc=RuntimeError("connection error"))

    entries = in_memory_logger.all()
    assert len(entries) == 2
    assert entries[0].level == "info"
    assert entries[0].message == "Service started"
    assert entries[0].extra == {"port": 8080}
    assert entries[1].level == "error"
    assert entries[1].message == "Database connection failed"
    assert isinstance(entries[1].exc, RuntimeError)
