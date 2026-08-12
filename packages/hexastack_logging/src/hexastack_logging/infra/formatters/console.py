import logging
from datetime import UTC, datetime

_LEVEL_COLORS = {
    "DEBUG": "\033[36m",  # Cyan
    "INFO": "\033[32m",  # Green
    "WARNING": "\033[33m",  # Yellow
    "ERROR": "\033[31m",  # Red
    "CRITICAL": "\033[1;31m",  # Bold Red
}
_RESET = "\033[0m"
_MUTED = "\033[90m"


class ConsoleFormatter(logging.Formatter):
    """Colorized human-readable console log formatter for development.

    Notes/Architectural Intent:
        Renders clear terminal log output with level-based ANSI colors, ISO timestamps,
        and correlation context tags.
    """

    def __init__(
        self,
        colorize: bool = True,
        datefmt: str = "%Y-%m-%d %H:%M:%S",
        include_context: bool = True,
    ) -> None:
        """Initialize ConsoleFormatter.

        Args:
            colorize: If True, applies ANSI color codes to log levels.
            datefmt: Strftime date format string.
            include_context: If True, displays correlation ID tags in log lines.
        """
        super().__init__(datefmt=datefmt)
        self._colorize = colorize
        self._datefmt = datefmt
        self._include_context = include_context

    def format(self, record: logging.LogRecord) -> str:
        """Format the specified record as a colorized console string.

        Args:
            record: The LogRecord to format.

        Returns:
            Formatted log message string.

        Raises:
            None.
        """
        time_str = datetime.fromtimestamp(
            record.created, tz=UTC
        ).strftime(self._datefmt)
        level_name = record.levelname

        if self._colorize:
            color = _LEVEL_COLORS.get(level_name, "")
            level_str = f"{color}[{level_name:<8}]{_RESET}"
            time_part = f"{_MUTED}[{time_str}]{_RESET}"
        else:
            level_str = f"[{level_name:<8}]"
            time_part = f"[{time_str}]"

        context_part = ""
        if self._include_context:
            cid = getattr(record, "correlation_id", "")
            if cid:
                context_part = (
                    f" {_MUTED}[corr:{cid[:8]}]{_RESET}"
                    if self._colorize
                    else f" [corr:{cid[:8]}]"
                )

        msg = record.getMessage()
        formatted = f"{time_part} {level_str}{context_part} {msg}"

        if record.exc_info:
            formatted += "\n" + self.formatException(record.exc_info)

        return formatted
