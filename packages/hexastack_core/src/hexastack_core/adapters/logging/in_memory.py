from dataclasses import dataclass

from hexastack_core.ports.logging import Extras, LoggingPort


@dataclass(frozen=True)
class LogEntry:
    """Immutable record representing a captured log message entry.

    Notes/Architectural Intent:
        Stores captured log parameters for test assertions, memory buffering,
        and log replay.
    """

    level: str
    message: str
    extra: Extras | None = None
    exc: Exception | None = None


class InMemoryLogger(LoggingPort):
    """In-memory logging adapter capturing log entries in an accessible list.

    Notes/Architectural Intent:
        Serves as a lightweight logging adapter for test verification, early boot buffering,
        and offline inspection without external logging handler side effects.
    """

    def __init__(self) -> None:
        """Initialize empty in-memory logger."""
        self._entries: list[LogEntry] = []

    def all(self) -> list[LogEntry]:
        """Retrieve all captured log entries in chronological order.

        Returns:
            List of all LogEntry records captured since initialization or last clear.

        Raises:
            None.
        """
        return list(self._entries)

    def clear(self) -> None:
        """Clear all stored log entries.

        Returns:
            None.

        Raises:
            None.
        """
        self._entries.clear()

    def debug(self, message: str, extra: Extras | None = None) -> None:
        """Capture a debug-level log entry.

        Args:
            message: Text message to log.
            extra: Optional key-value dictionary of contextual metadata.

        Returns:
            None.

        Raises:
            None.
        """
        self._entries.append(LogEntry(level="debug", message=message, extra=extra))

    @property
    def entries(self) -> list[LogEntry]:
        """Property returning list of all captured log entries.

        Returns:
            List of all LogEntry records captured.
        """
        return self.all()

    def entries_by_level(self, level: str) -> list[LogEntry]:
        """Filter and retrieve captured log entries matching a specific log level.

        Args:
            level: The target log level name (e.g. 'debug', 'info', 'warning', 'error').

        Returns:
            Filtered list of LogEntry records matching level.

        Raises:
            None.
        """
        return [entry for entry in self._entries if entry.level == level]

    def error(
        self, message: str, extra: Extras | None = None, exc: Exception | None = None
    ) -> None:
        """Capture an error-level log entry with optional exception.

        Args:
            message: Text message to log.
            extra: Optional key-value dictionary of contextual metadata.
            exc: Optional exception instance.

        Returns:
            None.

        Raises:
            None.
        """
        self._entries.append(
            LogEntry(level="error", message=message, extra=extra, exc=exc)
        )

    def info(self, message: str, extra: Extras | None = None) -> None:
        """Capture an info-level log entry.

        Args:
            message: Text message to log.
            extra: Optional key-value dictionary of contextual metadata.

        Returns:
            None.

        Raises:
            None.
        """
        self._entries.append(LogEntry(level="info", message=message, extra=extra))

    def warning(self, message: str, extra: Extras | None = None) -> None:
        """Capture a warning-level log entry.

        Args:
            message: Text message to log.
            extra: Optional key-value dictionary of contextual metadata.

        Returns:
            None.

        Raises:
            None.
        """
        self._entries.append(LogEntry(level="warning", message=message, extra=extra))
