"""Configuration hook for mutmut mutation testing.

Notes/Architectural Intent:
    Filters out non-functional AST mutations such as Pydantic Field(description=...),
    CLI help text strings, logger formatting literals, and docstring-like metadata
    to focus mutation testing purely on core business and operational logic.
"""

from __future__ import annotations

import re
from typing import Any

# Regex patterns identifying non-functional lines that should not be mutated
SKIP_LINE_PATTERNS = [
    re.compile(r"^\s*description\s*="),
    re.compile(r"^\s*help\s*="),
    re.compile(r"^\s*help_text\s*="),
    re.compile(r"^\s*instructions\s*="),
    re.compile(r"Field\([^)]*description\s*="),
    re.compile(
        r":\s*(?:bool|str|int|float|Literal|Sequence|list|dict|set)[^=]*=\s*Field\("
    ),
    re.compile(r"Option\([^)]*help\s*="),
    re.compile(r"doc\s*=\s*help_text\s*or"),
    re.compile(r"__signature__\s*="),
    re.compile(r"__all__\s*=\s*\["),
    re.compile(r"^\s*#"),
]


def pre_mutation(context: Any) -> None:
    """Mutmut hook executed prior to applying and running each mutation.

    Args:
        context: Mutmut Context object containing `filename`, `current_source_line`,
            and `skip` attribute.

    Returns:
        None.
    """
    line = getattr(context, "current_source_line", "") or ""

    # 1. Skip lines matching non-functional description or help text patterns
    for pattern in SKIP_LINE_PATTERNS:
        if pattern.search(line):
            context.skip = True
            return

    # 2. Skip inline pragma directives if present
    if "# pragma: no mutate" in line or "# no mutate" in line:
        context.skip = True
        return
