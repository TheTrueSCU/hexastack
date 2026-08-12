import importlib.util

import pytest
from hexastack_core.domain.exceptions import (
    HexastackError,
    MissingDependencyError,
)
from hexastack_logging.adapters.logger.rich import RichLogger


def test_rich_logger():
    if importlib.util.find_spec("rich") is None:
        with pytest.raises(
            MissingDependencyError, match="rich is required"
        ) as exc_info:
            RichLogger()
        assert isinstance(exc_info.value, HexastackError)
        return

    logger = RichLogger()
    logger.debug("Rich debug message")
    logger.info("Rich test message", extra={"key": "value"})
    logger.warning("Rich warning message")
    logger.error("Rich error message", exc=ValueError("test"))
    logger.critical("Rich critical message")
