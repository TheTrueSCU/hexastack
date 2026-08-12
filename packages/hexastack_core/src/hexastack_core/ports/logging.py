from abc import ABC, abstractmethod
from typing import Any

type Extras = dict[str, Any]


class LoggingPort(ABC):
    """Abstract port interface for structured logging operations.

    Notes/Architectural Intent:
        Abstracts system logging implementation details (e.g. structlog, standard logging)
        away from domain and application layers.
    """

    @abstractmethod
    def critical(
        self, message: str, extra: Extras | None = None, exc: Exception | None = None
    ) -> None:
        """Log a critical-level message with optional exception context.

        Args:
            message: Text message to log.
            extra: Optional key-value dictionary of contextual metadata.
            exc: Optional exception instance to log traceback for.

        Returns:
            None.

        Raises:
            None.
        """
        ...

    @abstractmethod
    def debug(self, message: str, extra: Extras | None = None) -> None:
        """Log a debug-level message.

        Args:
            message: Text message to log.
            extra: Optional key-value dictionary of contextual metadata.

        Returns:
            None.

        Raises:
            None.
        """
        ...

    @abstractmethod
    def error(
        self, message: str, extra: Extras | None = None, exc: Exception | None = None
    ) -> None:
        """Log an error-level message with optional exception context.

        Args:
            message: Text message to log.
            extra: Optional key-value dictionary of contextual metadata.
            exc: Optional exception instance to log traceback for.

        Returns:
            None.

        Raises:
            None.
        """
        ...

    @abstractmethod
    def info(self, message: str, extra: Extras | None = None) -> None:
        """Log an info-level message.

        Args:
            message: Text message to log.
            extra: Optional key-value dictionary of contextual metadata.

        Returns:
            None.

        Raises:
            None.
        """
        ...

    @abstractmethod
    def warning(self, message: str, extra: Extras | None = None) -> None:
        """Log a warning-level message.

        Args:
            message: Text message to log.
            extra: Optional key-value dictionary of contextual metadata.

        Returns:
            None.

        Raises:
            None.
        """
        ...
