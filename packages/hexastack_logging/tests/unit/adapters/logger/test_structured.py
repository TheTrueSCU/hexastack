import logging

from hexastack_logging.adapters.logger.structured import StructuredLogger


class ListHandler(logging.Handler):
    def __init__(self) -> None:
        super().__init__()
        self.records: list[logging.LogRecord] = []

    def emit(self, record: logging.LogRecord) -> None:
        self.records.append(record)


def test_structured_logger_methods():
    raw_logger = logging.getLogger("test_structured_logger")
    raw_logger.setLevel(logging.DEBUG)
    handler = ListHandler()
    raw_logger.addHandler(handler)

    logger = StructuredLogger(logger=raw_logger)

    logger.debug("debug message", extra={"user_id": "123"})
    logger.info("info message", extra={"action": "create"})
    logger.warning("warning message")
    logger.error("error message", extra={"code": 500})
    logger.critical("critical message")

    assert len(handler.records) == 5
    assert handler.records[0].levelname == "DEBUG"
    assert handler.records[0].getMessage() == "debug message"
    assert handler.records[0].__dict__.get("user_id") == "123"

    assert handler.records[1].levelname == "INFO"
    assert handler.records[1].__dict__.get("action") == "create"

    assert handler.records[2].levelname == "WARNING"
    assert handler.records[3].levelname == "ERROR"
    assert handler.records[4].levelname == "CRITICAL"


def test_structured_logger_listener_close_and_default_init():
    from unittest.mock import MagicMock

    mock_listener = MagicMock()
    logger = StructuredLogger(
        logger=logging.getLogger("custom"), listener=mock_listener
    )
    assert logger._listener is mock_listener

    logger.close()
    mock_listener.stop.assert_called_once()
    assert logger._listener is None

    # Idempotent close
    logger.close()

    # Default init without pre-built logger
    default_logger = StructuredLogger(name="default_test_app")
    assert default_logger._logger.name == "default_test_app"
    default_logger.close()
