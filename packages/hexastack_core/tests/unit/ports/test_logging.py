import inspect

import pytest

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


def test_logging_port_is_abstract() -> None:
    """Verify that LoggingPort cannot be instantiated directly and is abstract."""
    is_abs = inspect.isabstract(LoggingPort)
    assert is_abs is True
    with pytest.raises(TypeError, match="Can't instantiate abstract class"):
        LoggingPort()  # ty: ignore[call-non-callable] # type: ignore[abstract]


def test_logging_port_abstract_methods() -> None:
    """Verify abstract methods on LoggingPort."""
    expected = {"critical", "debug", "error", "info", "warning"}
    abstracts = LoggingPort.__abstractmethods__
    diff = expected.difference(abstracts)
    assert len(diff) == 0
