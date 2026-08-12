import importlib.util

import pytest
from hexastack_core.domain.exceptions import (
    HexastackError,
    MissingDependencyError,
)
from hexastack_logging.adapters.logger.loguru import LoguruAdapter


def test_loguru_adapter():
    if importlib.util.find_spec("loguru") is None:
        with pytest.raises(
            MissingDependencyError, match="loguru is required"
        ) as exc_info:
            LoguruAdapter()
        assert isinstance(exc_info.value, HexastackError)
        return

    adapter = LoguruAdapter()
    adapter.debug("Loguru debug message")
    adapter.info("Loguru message", extra={"key": "value"})
    adapter.warning("Loguru warning message")
    adapter.error("Loguru error message", exc=ValueError("test"))
    adapter.critical("Loguru critical message")
