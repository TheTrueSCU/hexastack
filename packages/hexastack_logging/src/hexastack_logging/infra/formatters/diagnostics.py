"""Frame-level variable diagnostic formatter powered by stackprinter.

Notes/Architectural Intent:
    Renders granular, frame-level exception traces that capture local variables,
    arguments, and source line highlights at the point of failure.
    Applies automatic secret redaction via suppressed variable patterns and LogSanitizer
    to ensure credentials and PII are never leaked into log sinks or error responses.
"""

import logging
import re
from typing import Any

from hexastack_core.utils.imports import require_dependency
from hexastack_logging.utils.sanitizer import DEFAULT_MASKED_KEYS, LogSanitizer

__all__ = [
    "DiagnosticExceptionFormatter",
    "format_diagnostics",
]

_DEFAULT_SUPPRESSED_PATTERNS = tuple(
    rf".*{re.escape(k)}.*" for k in sorted(DEFAULT_MASKED_KEYS)
)


class DiagnosticExceptionFormatter(logging.Formatter):
    """Rich exception formatter displaying annotated local variables with sensitive masking.

    Notes/Architectural Intent:
        Extends standard logging.Formatter, overriding formatException to emit
        structured frame diagnostics with stackprinter. Automatically redacts
        sensitive variable names (passwords, tokens, keys) and scrubs inline PII.
    """

    def __init__(
        self,
        fmt: str | None = None,
        datefmt: str | None = None,
        style: str = "plaintext",
        source_lines: int = 5,
        show_vals: str | None = "all",
        truncate_vals: int = 500,
        line_wrap: int = 60,
        suppressed_vars: list[str] | tuple[str, ...] | None = None,
        sanitize: bool = True,
    ) -> None:
        """Initialize DiagnosticExceptionFormatter.

        Args:
            fmt: Log message format string.
            datefmt: Date format string.
            style: Color/terminal style ('plaintext', 'darkbg', 'lightbg', etc.).
            source_lines: Number of source lines to show around failure site.
            show_vals: Variable visibility mode ('all', 'like_source', 'line', or None).
            truncate_vals: Maximum character length for each serialized variable.
            line_wrap: Column width for wrapping variable values.
            suppressed_vars: Regex patterns of variable names to suppress.
            sanitize: Whether to scrub inline tokens/PII using LogSanitizer.

        Raises:
            MissingDependencyError: If stackprinter is not installed.
        """
        super().__init__(fmt=fmt, datefmt=datefmt)
        self._stackprinter = require_dependency(
            "stackprinter",
            extra="diagnostics",
            package="hexastack-logging",
            feature_name="DiagnosticExceptionFormatter",
        )
        self._diagnostic_style = style
        self._source_lines = source_lines
        self._show_vals = show_vals
        self._truncate_vals = truncate_vals
        self._line_wrap = line_wrap
        self._suppressed_vars = list(
            suppressed_vars
            if suppressed_vars is not None
            else _DEFAULT_SUPPRESSED_PATTERNS
        )
        self._sanitize = sanitize
        self._sanitizer = LogSanitizer() if sanitize else None

    def format_exception(
        self,
        exc: BaseException | tuple[Any, Any, Any] | None = None,
    ) -> str:
        """Render frame-level exception diagnostics.

        Args:
            exc: Exception instance, sys.exc_info() tuple, or None (active exception).

        Returns:
            Human-readable, redacted exception diagnostics string.

        Raises:
            None.
        """
        output: str = self._stackprinter.format(
            exc,
            style=self._diagnostic_style,
            source_lines=self._source_lines,
            show_vals=self._show_vals,
            truncate_vals=self._truncate_vals,
            line_wrap=self._line_wrap,
            suppressed_vars=self._suppressed_vars,
        )
        if self._sanitizer is not None:
            output = self._sanitizer.sanitize_traceback(output)
        return output

    def formatException(self, ei: Any) -> str:
        """Format an exception tuple for logging integration.

        Args:
            ei: Standard sys.exc_info() tuple (type, value, traceback).

        Returns:
            Formatted exception traceback with frame variables.

        Raises:
            None.
        """
        return self.format_exception(ei)


def format_diagnostics(
    exc: BaseException | tuple[Any, Any, Any] | None = None,
    style: str = "plaintext",
    source_lines: int = 5,
    show_vals: str | None = "all",
    truncate_vals: int = 500,
    line_wrap: int = 60,
    suppressed_vars: list[str] | tuple[str, ...] | None = None,
    sanitize: bool = True,
) -> str:
    """Format an exception with frame variables and automatic secret redaction.

    Notes/Architectural Intent:
        Convenience function for generating diagnostic failure dumps in HTTP error
        middleware, task queues (Hexaqueue `hq why`), or worker crash logs.

    Args:
        exc: Exception instance, sys.exc_info() tuple, or None (active exception).
        style: Output styling ('plaintext', 'darkbg', etc.).
        source_lines: Number of source lines to display around failure point.
        show_vals: Which variables to display ('all', 'like_source', 'line', None).
        truncate_vals: Maximum character length for variable values.
        line_wrap: Column limit for variable value formatting.
        suppressed_vars: Regex patterns of variable names to suppress.
        sanitize: Whether to scrub inline tokens/PII using LogSanitizer.

    Returns:
        Formatted and sanitized diagnostic trace string.

    Raises:
        MissingDependencyError: If stackprinter is not installed.
    """
    formatter = DiagnosticExceptionFormatter(
        style=style,
        source_lines=source_lines,
        show_vals=show_vals,
        truncate_vals=truncate_vals,
        line_wrap=line_wrap,
        suppressed_vars=suppressed_vars,
        sanitize=sanitize,
    )
    return formatter.format_exception(exc)
