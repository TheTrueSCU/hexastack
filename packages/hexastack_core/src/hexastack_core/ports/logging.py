from abc import ABC, abstractmethod
from typing import Any, TypeAlias

Extras: TypeAlias = dict[str, Any]


class LoggingPort(ABC):
    """Abstract port interface for structured logging operations.

    Notes/Architectural Intent:
        Abstracts system logging implementation details (e.g. structlog, standard logging)
        away from domain and application layers.
    """

    @abstractmethod
    def critical(
        self,
        message: str,
        extra: Extras | None = None,
        exc: Exception | None = None,
    ) -> None:
        """Log a critical-level message with optional exception context."""
        ...

    @abstractmethod
    def debug(self, message: str, extra: Extras | None = None) -> None:
        """Log a debug-level message."""
        ...

    @abstractmethod
    def error(
        self,
        message: str,
        extra: Extras | None = None,
        exc: Exception | None = None,
    ) -> None:
        """Log an error-level message with optional exception context."""
        ...

    @abstractmethod
    def info(self, message: str, extra: Extras | None = None) -> None:
        """Log an info-level message."""
        ...

    @abstractmethod
    def warning(self, message: str, extra: Extras | None = None) -> None:
        """Log a warning-level message."""
        ...


__all__ = [
    "Extras",
    "LoggingPort",
]
