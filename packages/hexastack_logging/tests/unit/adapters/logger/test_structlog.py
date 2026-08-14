import importlib.util

import pytest

from hexastack_core.domain.exceptions import (
    HexastackError,
    MissingDependencyError,
)
from hexastack_logging.adapters.logger.structlog import StructlogAdapter


def test_structlog_adapter():
    if importlib.util.find_spec("structlog") is None:
        with pytest.raises(
            MissingDependencyError, match="structlog is required"
        ) as exc_info:
            StructlogAdapter()
        assert isinstance(exc_info.value, HexastackError)
        return

    adapter = StructlogAdapter()
    adapter.debug("Structlog debug message")
    adapter.info("Structlog message", extra={"key": "value"})
    adapter.warning("Structlog warning message")
    adapter.error("Structlog error message", exc=ValueError("test"))
    adapter.critical("Structlog critical message")
