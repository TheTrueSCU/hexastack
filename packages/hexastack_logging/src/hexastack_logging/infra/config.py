import logging
import queue
from logging.handlers import (
    QueueHandler,
    QueueListener,
    RotatingFileHandler,
    TimedRotatingFileHandler,
)
from pathlib import Path

from hexastack_core.infra.decorators import config_section
from hexastack_core.infra.registries.config import ConfigRegistry
from hexastack_logging.domain.config import (
    AsyncQueueConfig,
    FileLoggingConfig,
    HexastackLoggingConfig,
    SanitizerConfig,
)
from hexastack_logging.infra.filters import (
    CorrelationIdFilter,
    SanitizerFilter,
)
from hexastack_logging.infra.formatters.console import ConsoleFormatter
from hexastack_logging.infra.formatters.json import JsonFormatter
from hexastack_logging.infra.sanitizer import (
    Sanitizer,
)

config_section("logging")(HexastackLoggingConfig)

__all__ = [
    "AsyncQueueConfig",
    "configure_logging",
    "FileLoggingConfig",
    "HexastackLoggingConfig",
    "register_logging_config",
    "SanitizerConfig",
]


def _get_formatter(
    fmt: str,
    colorize: bool,
    datefmt: str,
    include_context: bool,
) -> logging.Formatter:
    """Instantiate appropriate Formatter based on format type."""
    if fmt == "json":
        return JsonFormatter(include_context=include_context)
    return ConsoleFormatter(
        colorize=colorize,
        datefmt=datefmt,
        include_context=include_context,
    )


def _prepare_file_handler(
    cfg: HexastackLoggingConfig,
    level_num: int,
    correlation_filter: CorrelationIdFilter,
    sanitizer_filter: SanitizerFilter | None,
) -> logging.Handler:
    """Create and configure rotating file handler."""
    log_file_path = Path(cfg.file.path)
    log_file_path.parent.mkdir(parents=True, exist_ok=True)

    file_formatter = _get_formatter(
        fmt=cfg.file.format,
        colorize=False,
        datefmt=cfg.datefmt,
        include_context=cfg.include_context,
    )

    file_handler: logging.Handler
    if cfg.file.rotation_type == "time":
        file_handler = TimedRotatingFileHandler(
            filename=str(log_file_path),
            when=cfg.file.when,
            backupCount=cfg.file.backup_count,
            encoding="utf-8",
        )
    else:
        file_handler = RotatingFileHandler(
            filename=str(log_file_path),
            maxBytes=cfg.file.max_bytes,
            backupCount=cfg.file.backup_count,
            encoding="utf-8",
        )

    file_handler.setLevel(level_num)
    file_handler.setFormatter(file_formatter)
    file_handler.addFilter(correlation_filter)
    if sanitizer_filter:
        file_handler.addFilter(sanitizer_filter)
    return file_handler


def configure_logging(
    config: HexastackLoggingConfig | None = None,
    target_logger: logging.Logger | None = None,
) -> QueueListener | None:
    """Configure a Python logging.Logger with filters, sanitization, file rotation, and async queues.

    Args:
        config: Optional HexastackLoggingConfig instance (defaults to standard settings).
        target_logger: Optional Logger to configure (defaults to root logger).

    Returns:
        The started QueueListener instance if async queueing is enabled, otherwise None.

    Raises:
        None.
    """
    cfg = config or HexastackLoggingConfig()
    logger = target_logger or logging.getLogger()

    # 1. Set global log level
    level_num = getattr(logging, cfg.level.upper(), logging.INFO)
    logger.setLevel(level_num)

    # 2. Configure per-module / fine-grained log levels
    for mod_name, mod_level in cfg.loggers.items():
        sub_level = getattr(logging, mod_level.upper(), logging.INFO)
        logging.getLogger(mod_name).setLevel(sub_level)

    # 3. Prepare filters
    correlation_filter = CorrelationIdFilter()
    sanitizer_filter: SanitizerFilter | None = None
    if cfg.sanitizer.enable:
        san = Sanitizer(
            masked_keys=cfg.sanitizer.masked_keys,
            mask_replacement=cfg.sanitizer.mask_replacement,
            regex_patterns=cfg.sanitizer.regex_patterns,
        )
        sanitizer_filter = SanitizerFilter(san)

    # 4. Prepare Stream (Console) Handler
    stream_formatter = _get_formatter(
        fmt=cfg.format,
        colorize=cfg.colorize,
        datefmt=cfg.datefmt,
        include_context=cfg.include_context,
    )
    stream_handler = logging.StreamHandler()
    stream_handler.setLevel(level_num)
    stream_handler.setFormatter(stream_formatter)
    stream_handler.addFilter(correlation_filter)
    if sanitizer_filter:
        stream_handler.addFilter(sanitizer_filter)

    sink_handlers: list[logging.Handler] = [stream_handler]

    # 5. Prepare File Handler if enabled
    if cfg.file.enable:
        sink_handlers.append(
            _prepare_file_handler(cfg, level_num, correlation_filter, sanitizer_filter)
        )

    # 6. Apply Async Queue or Direct Handlers
    logger.handlers.clear()
    listener: QueueListener | None = None
    if cfg.queue.enable:
        log_queue: queue.Queue[logging.LogRecord] = queue.Queue(
            maxsize=cfg.queue.max_size
        )
        queue_handler = QueueHandler(log_queue)
        queue_handler.setLevel(level_num)
        queue_handler.addFilter(correlation_filter)
        if sanitizer_filter:
            queue_handler.addFilter(sanitizer_filter)

        listener = QueueListener(log_queue, *sink_handlers, respect_handler_level=True)
        listener.start()
        logger.addHandler(queue_handler)
    else:
        for h in sink_handlers:
            logger.addHandler(h)

    return listener


def register_logging_config(registry: ConfigRegistry) -> None:
    """Register logging configuration schema with a ConfigRegistry under 'logging'.

    Args:
        registry: Target ConfigRegistry instance.
    """
    registry.register_config_section("logging", HexastackLoggingConfig)
