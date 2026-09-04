import logging
from logging.handlers import QueueListener

from hexastack_core.ports.logging import Extras, LoggingPort
from hexastack_logging.domain.config import HexastackLoggingConfig


class StructuredLogger(LoggingPort):
    """Production-grade structured logger implementing LoggingPort.

    Notes/Architectural Intent:
        Delegates to standard library logging.Logger configured with CorrelationIdFilter,
        SanitizerFilter, rotating file handlers, and optional background QueueListener.
    """

    def __init__(
        self,
        logger: logging.Logger | None = None,
        listener: QueueListener | None = None,
        name: str = "hexastack",
        config: HexastackLoggingConfig | None = None,
    ) -> None:
        """Initialize StructuredLogger with logger instance, optional listener, or config.

        Args:
            logger: Pre-configured logging.Logger instance (or created via name).
            listener: Optional active QueueListener instance.
            name: Default logger hierarchy name if logger is not provided.
            config: Optional HexastackLoggingConfig instance.
        """
        self._logger = logger or logging.getLogger(name)
        self._listener = listener
        self._config = config

    def close(self) -> None:
        """Stop and flush the background QueueListener if active.

        Returns:
            None.

        Raises:
            None.
        """
        if self._listener is not None:
            self._listener.stop()
            self._listener = None

    def critical(
        self, message: str, extra: Extras | None = None, exc: Exception | None = None
    ) -> None:
        """Log a critical message with extra context.

        Args:
            message: The message string to log.
            extra: Optional key-value dictionary of contextual metadata.
            exc: Optional exception instance to attach traceback.

        Returns:
            None.

        Raises:
            None.
        """
        self._logger.critical(message, exc_info=exc, extra=extra)

    def debug(self, message: str, extra: Extras | None = None) -> None:
        """Log a debug message with extra context.

        Args:
            message: The message string to log.
            extra: Optional key-value dictionary of contextual metadata.

        Returns:
            None.

        Raises:
            None.
        """
        self._logger.debug(message, extra=extra)

    def error(
        self, message: str, extra: Extras | None = None, exc: Exception | None = None
    ) -> None:
        """Log an error message with extra context.

        Args:
            message: The message string to log.
            extra: Optional key-value dictionary of contextual metadata.
            exc: Optional exception instance to attach traceback.

        Returns:
            None.

        Raises:
            None.
        """
        self._logger.error(message, exc_info=exc, extra=extra)

    def info(self, message: str, extra: Extras | None = None) -> None:
        """Log an informational message with extra context.

        Args:
            message: The message string to log.
            extra: Optional key-value dictionary of contextual metadata.

        Returns:
            None.

        Raises:
            None.
        """
        self._logger.info(message, extra=extra)

    @property
    def listener(self) -> QueueListener | None:
        """The active QueueListener instance if async queueing is enabled."""
        return self._listener

    def warning(self, message: str, extra: Extras | None = None) -> None:
        """Log a warning message with extra context.

        Args:
            message: The message string to log.
            extra: Optional key-value dictionary of contextual metadata.

        Returns:
            None.

        Raises:
            None.
        """
        self._logger.warning(message, extra=extra)
