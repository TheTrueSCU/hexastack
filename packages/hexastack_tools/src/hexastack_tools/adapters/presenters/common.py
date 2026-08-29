"""Common presentation utilities and pipe-detection for hexastack_tools."""

from __future__ import annotations

import sys

from hexastack_tools.domain.github import OutputFormat


def resolve_output_format(output_format: OutputFormat) -> OutputFormat:
    """Resolve auto output format: automatically selects PLAIN if stdout is piped (not a TTY).

    Args:
        output_format: Requested output format mode (AUTO, RICH, JSON, PLAIN).

    Returns:
        Resolved concrete OutputFormat (RICH, JSON, or PLAIN).
    """
    if output_format == OutputFormat.AUTO:
        return OutputFormat.PLAIN if not sys.stdout.isatty() else OutputFormat.RICH
    return output_format


__all__ = [
    "resolve_output_format",
]
