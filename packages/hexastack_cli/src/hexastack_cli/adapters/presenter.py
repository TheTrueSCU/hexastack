import json
import os
import sys
from typing import Any

from pydantic import BaseModel
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from hexastack_core.domain import Generic
from hexastack_core.ports.presenter import PresenterPort


class RichTerminalPresenter(PresenterPort):
    """Terminal presenter formatting domain models into stylized Rich panels, JSON, or plain text.

    Notes/Architectural Intent:
        Implements Presenter port for terminal and CI/pipe environments.
        Supports structured JSON, plain line-oriented text, and interactive Rich tables.
        Automatically respects NO_COLOR and non-TTY stdout streams.
    """

    def __init__(
        self,
        console: Console | None = None,
        stderr_console: Console | None = None,
    ) -> None:
        """Initialize RichTerminalPresenter with optional stdout and stderr Console instances.

        Args:
            console: Optional rich.console.Console instance for stdout.
            stderr_console: Optional rich.console.Console instance for stderr.
        """
        no_color = bool(os.environ.get("NO_COLOR"))
        self._console = console or Console(no_color=no_color, highlight=not no_color)
        self._stderr = stderr_console or Console(
            stderr=True, no_color=no_color, highlight=not no_color
        )

    def present(
        self,
        instance: Generic,
        format_mode: str | None = None,
    ) -> Any:
        """Format and print a domain Generic instance to stdout based on requested format mode.

        Args:
            instance: Domain Generic or DTO model instance.
            format_mode: Optional format mode ('table', 'json', 'plain').

        Returns:
            The presented raw data representation.

        Raises:
            None.
        """
        data = instance.model_dump() if isinstance(instance, BaseModel) else instance

        mode = (format_mode or "table").lower()

        if mode == "json":
            return self._present_json(data)
        if mode == "plain":
            return self._present_plain(data)
        return self._present_table(instance, data)

    def print_error(self, message: str) -> None:
        """Print an error message to stderr.

        Args:
            message: The error message string.

        Returns:
            None.

        Raises:
            None.
        """
        self._stderr.print(f"[bold red]Error:[/bold red] {message}")

    def print_exception(self) -> None:
        """Print a rich formatted traceback to stderr for debugging.

        Returns:
            None.

        Raises:
            None.
        """
        self._stderr.print_exception(show_locals=False)

    def _present_json(self, data: Any) -> Any:
        """Render raw, pipe-friendly JSON to stdout."""
        json_str = json.dumps(data, indent=2, default=str)
        sys.stdout.write(json_str + "\n")
        sys.stdout.flush()
        return data

    def _present_plain(self, data: Any) -> Any:
        """Render TSV/newline-delimited text to stdout for Unix pipeline processing."""
        if isinstance(data, dict):
            for k, v in data.items():
                sys.stdout.write(f"{k}\t{v}\n")
        elif isinstance(data, list):
            for item in data:
                sys.stdout.write(f"{item}\n")
        else:
            sys.stdout.write(f"{data}\n")
        sys.stdout.flush()
        return data

    def _present_table(self, instance: Generic, data: Any) -> Any:
        """Render colorized Rich table/panel to stdout."""
        if isinstance(data, dict):
            table = Table(show_header=True, header_style="bold magenta")
            table.add_column("Field", style="cyan")
            table.add_column("Value", style="green")
            for k, v in data.items():
                val_str = (
                    json.dumps(v, indent=2) if isinstance(v, dict | list) else str(v)
                )
                table.add_row(str(k), val_str)
            self._console.print(
                Panel(table, title=type(instance).__name__, border_style="blue")
            )
        elif isinstance(data, list):
            for item in data:
                self._console.print(f"[cyan]•[/cyan] {item}")
        else:
            self._console.print(f"[bold green]{data}[/bold green]")
        return data


__all__ = [
    "RichTerminalPresenter",
]
