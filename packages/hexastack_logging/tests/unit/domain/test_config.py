from hexastack_logging.domain.config import (
    AsyncQueueConfig,
    FileLoggingConfig,
    HexastackLoggingConfig,
    SanitizerConfig,
)


def test_hexastack_logging_config_defaults():
    cfg = HexastackLoggingConfig()
    assert cfg.level == "INFO"
    assert cfg.format == "console"
    assert cfg.colorize is True
    assert isinstance(cfg.sanitizer, SanitizerConfig)
    assert isinstance(cfg.file, FileLoggingConfig)
    assert isinstance(cfg.queue, AsyncQueueConfig)
