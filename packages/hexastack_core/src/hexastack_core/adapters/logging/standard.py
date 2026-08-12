import logging

from hexastack_core.ports.logging import Extras, LoggingPort


class StandardLogger(LoggingPort):
    """Logging adapter bridging LoggingPort to Python's standard library logging module.

    Notes/Architectural Intent:
        Wraps standard library logging.Logger instances to provide baseline console/file logging
        without requiring external logging dependencies.
    """

    def __init__(self, logger: logging.Logger | str | None = None) -> None:
        """Initialize StandardLogger with a standard library Logger or logger name.

        Args:
            logger: Optional logging.Logger instance or string logger name. Defaults to "hexastack".
        """
        if isinstance(logger, logging.Logger):
            self._logger = logger
        elif isinstance(logger, str):
            self._logger = logging.getLogger(logger)
        else:
            self._logger = logging.getLogger("hexastack")

    def debug(self, message: str, extra: Extras | None = None) -> None:
        """Emit a debug-level log message to the underlying standard logger.

        Args:
            message: Text message to log.
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
        """Emit an error-level log message to the underlying standard logger.

        Args:
            message: Text message to log.
            extra: Optional key-value dictionary of contextual metadata.
            exc: Optional exception instance to attach traceback.

        Returns:
            None.

        Raises:
            None.
        """
        self._logger.error(message, exc_info=exc, extra=extra)

    def info(self, message: str, extra: Extras | None = None) -> None:
        """Emit an info-level log message to the underlying standard logger.

        Args:
            message: Text message to log.
            extra: Optional key-value dictionary of contextual metadata.

        Returns:
            None.

        Raises:
            None.
        """
        self._logger.info(message, extra=extra)

    def warning(self, message: str, extra: Extras | None = None) -> None:
        """Emit a warning-level log message to the underlying standard logger.

        Args:
            message: Text message to log.
            extra: Optional key-value dictionary of contextual metadata.

        Returns:
            None.

        Raises:
            None.
        """
        self._logger.warning(message, extra=extra)
