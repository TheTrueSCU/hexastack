import json
import logging
import time
from pathlib import Path

from hexastack_core.infra.registries.config import ConfigRegistry
from hexastack_logging.adapters.logger.structured import StructuredLogger
from hexastack_logging.infra.config import (
    AsyncQueueConfig,
    FileLoggingConfig,
    HexastackLoggingConfig,
    configure_logging,
    register_logging_config,
)


def test_configure_logging_async_queue_and_structured_logger(tmp_path: Path):
    log_file = tmp_path / "async_test.log"

    cfg = HexastackLoggingConfig(
        level="INFO",
        queue=AsyncQueueConfig(enable=True, max_size=1000),
        file=FileLoggingConfig(enable=True, path=str(log_file)),
    )

    structured = StructuredLogger(name="test_async_structured", config=cfg)
    assert structured.listener is not None

    structured.info("Async queue log message")
    time.sleep(0.05)  # Allow background queue worker to drain

    # Stop background listener cleanly via instance
    structured.close()
    assert structured.listener is None

    assert log_file.exists()
    content = log_file.read_text(encoding="utf-8")
    assert "Async queue log message" in content


def test_configure_logging_file_and_per_module_levels(tmp_path: Path):
    log_file = tmp_path / "subdir" / "test.log"
    logger = logging.getLogger("test_file_logger")

    cfg = HexastackLoggingConfig(
        level="INFO",
        file=FileLoggingConfig(
            enable=True,
            path=str(log_file),
            format="json",
            max_bytes=1024,
            backup_count=2,
            rotation_type="size",
        ),
        loggers={"noisy.module": "ERROR"},
    )
    listener = configure_logging(config=cfg, target_logger=logger)
    assert listener is None

    # 1. Check fine-grained log levels
    assert logging.getLogger("noisy.module").level == logging.ERROR

    # 2. Check stream and file handlers
    assert len(logger.handlers) == 2
    logger.info("File log test message")

    # Flush file handlers
    for h in logger.handlers:
        h.flush()

    assert log_file.exists()
    content = log_file.read_text(encoding="utf-8")
    assert "File log test message" in content
    parsed = json.loads(content.strip().splitlines()[-1])
    assert parsed["message"] == "File log test message"


def test_configure_logging_file_time_rotation(tmp_path: Path):
    log_file = tmp_path / "time_rotated.log"
    logger = logging.getLogger("test_time_file_logger")

    cfg = HexastackLoggingConfig(
        level="INFO",
        file=FileLoggingConfig(
            enable=True,
            path=str(log_file),
            format="console",
            rotation_type="time",
            when="midnight",
            backup_count=3,
        ),
    )
    listener = configure_logging(config=cfg, target_logger=logger)
    assert listener is None
    assert len(logger.handlers) == 2
    logger.info("Time rotation test message")

    for h in logger.handlers:
        h.flush()
    assert log_file.exists()


def test_configure_logging_json():
    logger = logging.getLogger("test_config_json_logger")
    cfg = HexastackLoggingConfig(level="DEBUG", format="json")
    listener = configure_logging(config=cfg, target_logger=logger)

    assert listener is None
    assert logger.level == logging.DEBUG
    assert len(logger.handlers) == 1
    assert logger.handlers[0].formatter.__class__.__name__ == "JsonFormatter"


def test_register_logging_config():
    reg = ConfigRegistry()
    register_logging_config(reg)

    assert "logging" in reg
    assert reg.get("logging") == HexastackLoggingConfig


def test_sanitizer_config():
    cfg = HexastackLoggingConfig.model_validate(
        {"sanitizer": {"enable": False, "mask_replacement": "[HIDDEN]"}}
    )
    assert cfg.sanitizer.enable is False
    assert cfg.sanitizer.mask_replacement == "[HIDDEN]"

    logger = logging.getLogger("test_no_sanitizer")
    listener = configure_logging(config=cfg, target_logger=logger)
    assert listener is None
