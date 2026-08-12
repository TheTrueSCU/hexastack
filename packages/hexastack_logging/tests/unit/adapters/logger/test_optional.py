import importlib.util

import pytest
from hexastack_logging.adapters.logger.loguru import LoguruAdapter
from hexastack_logging.adapters.logger.rich import RichLogger
from hexastack_logging.adapters.logger.structlog import StructlogAdapter


def test_rich_logger():
    if importlib.util.find_spec("rich") is None:
        with pytest.raises(ImportError, match="rich is required"):
            RichLogger()
        return

    logger = RichLogger()
    logger.info("Rich test message", extra={"key": "value"})


def test_structlog_adapter():
    if importlib.util.find_spec("structlog") is None:
        with pytest.raises(ImportError, match="structlog is required"):
            StructlogAdapter()
        return

    adapter = StructlogAdapter()
    adapter.info("Structlog message")


def test_loguru_adapter():
    if importlib.util.find_spec("loguru") is None:
        with pytest.raises(ImportError, match="loguru is required"):
            LoguruAdapter()
        return

    adapter = LoguruAdapter()
    adapter.info("Loguru message")
