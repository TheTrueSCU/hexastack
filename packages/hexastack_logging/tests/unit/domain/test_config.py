from hexastack_logging.domain.config import (
    AsyncQueueConfig,
    FileLoggingConfig,
    HexastackLoggingConfig,
    LogSanitizerConfig,
    SentryLoggingConfig,
)


def test_hexastack_logging_config_defaults():
    cfg = HexastackLoggingConfig()
    level = cfg.level
    assert level == "INFO"
    fmt = cfg.format
    assert fmt == "console"
    col = cfg.colorize
    assert col is True
    assert isinstance(cfg.sanitizer, LogSanitizerConfig)
    assert isinstance(cfg.file, FileLoggingConfig)
    assert isinstance(cfg.queue, AsyncQueueConfig)
    assert isinstance(cfg.sentry, SentryLoggingConfig)
    sentry_enabled = cfg.sentry.enable
    assert sentry_enabled is False
    sentry_env = cfg.sentry.environment
    assert sentry_env == "development"
