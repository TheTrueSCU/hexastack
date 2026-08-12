import importlib
from typing import Any

from hexastack_core.domain.exceptions import MissingDependencyError
from hexastack_core.ports.logging import Extras, LoggingPort
from hexastack_core.utils.context import get_correlation_id


class RichLogger(LoggingPort):
    """Optional Rich terminal logger implementing LoggingPort.

    Notes/Architectural Intent:
        Renders rich stylized terminal logs with correlation ID tags when rich is installed.
    """

    def __init__(self, console: Any = None) -> None:
        """Initialize RichLogger.

        Args:
            console: Optional rich.console.Console instance.

        Raises:
            MissingDependencyError: If rich package is not installed.
        """
        if console is None:
            try:
                rich_console_mod = importlib.import_module("rich.console")
                self._console: Any = rich_console_mod.Console()
            except ImportError as err:
                raise MissingDependencyError(
                    "rich is required for RichLogger. Install via 'pip install hexastack-logging[rich]'."
                ) from err
        else:
            self._console = console

    def _render(
        self,
        level: str,
        color: str,
        message: str,
        extra: Extras | None = None,
        exc: Exception | None = None,
    ) -> None:
        cid = get_correlation_id()
        cid_tag = f"[dim][corr:{cid[:8]}][/dim] " if cid else ""
        extra_str = f" [dim]{extra}[/dim]" if extra else ""
        exc_str = f"\n[red]{exc}[/red]" if exc else ""
        self._console.print(
            f"[{color}][{level:<8}][/{color}] {cid_tag}{message}{extra_str}{exc_str}"
        )

    def critical(
        self, message: str, extra: Extras | None = None, exc: Exception | None = None
    ) -> None:
        """Log a critical message with Rich formatting.

        Args:
            message: Text message to log.
            extra: Optional key-value dictionary of contextual metadata.
            exc: Optional exception instance to attach traceback.

        Returns:
            None.

        Raises:
            None.
        """
        self._render("CRITICAL", "bold red", message, extra=extra, exc=exc)

    def debug(self, message: str, extra: Extras | None = None) -> None:
        """Log a debug message with Rich formatting.

        Args:
            message: Text message to log.
            extra: Optional key-value dictionary of contextual metadata.

        Returns:
            None.

        Raises:
            None.
        """
        self._render("DEBUG", "cyan", message, extra=extra)

    def error(
        self, message: str, extra: Extras | None = None, exc: Exception | None = None
    ) -> None:
        """Log an error message with Rich formatting.

        Args:
            message: Text message to log.
            extra: Optional key-value dictionary of contextual metadata.
            exc: Optional exception instance to attach traceback.

        Returns:
            None.

        Raises:
            None.
        """
        self._render("ERROR", "red", message, extra=extra, exc=exc)

    def info(self, message: str, extra: Extras | None = None) -> None:
        """Log an informational message with Rich formatting.

        Args:
            message: Text message to log.
            extra: Optional key-value dictionary of contextual metadata.

        Returns:
            None.

        Raises:
            None.
        """
        self._render("INFO", "green", message, extra=extra)

    def warning(self, message: str, extra: Extras | None = None) -> None:
        """Log a warning message with Rich formatting.

        Args:
            message: Text message to log.
            extra: Optional key-value dictionary of contextual metadata.

        Returns:
            None.

        Raises:
            None.
        """
        self._render("WARNING", "yellow", message, extra=extra)
