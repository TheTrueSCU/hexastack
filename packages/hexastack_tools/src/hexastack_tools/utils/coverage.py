"""Pure git diff hunk parsing and line correlation utilities.

Notes/Architectural Intent:
    Decouples raw git output processing from coverage database execution
    and pytest runners.
"""

from __future__ import annotations

import re
from collections import defaultdict
from pathlib import Path

__all__ = [
    "parse_git_diff_hunks",
]

_HUNK_RE = re.compile(r"^@@ -\d+(?:,\d+)? \+(\d+)(?:,(\d+))? @@")


def parse_git_diff_hunks(diff_stdout: str, root: Path) -> dict[Path, set[int]]:
    """Parse git diff output into a mapping of absolute file paths to modified line numbers.

    Args:
        diff_stdout: Output text from git diff -U0.
        root: Base repository root path for resolving relative diff paths.

    Returns:
        Mapping of absolute Path to set of 1-based modified line numbers.

    Notes/Architectural Intent:
        Enables Test Impact Analysis (TIA) by mapping modified lines back to
        coverage database test contexts without subprocess dependencies.
    """
    changed: dict[Path, set[int]] = defaultdict(set)
    current_file: Path | None = None

    for line in diff_stdout.splitlines():
        if line.startswith("+++ b/"):
            rel_path = line.removeprefix("+++ b/")
            current_file = (root / rel_path).resolve()
        elif line.startswith("@@") and current_file is not None:
            match = _HUNK_RE.match(line)
            if not match:
                continue

            start = int(match.group(1))
            count = int(match.group(2)) if match.group(2) is not None else 1

            if count > 0:
                lines = range(start, start + count)
                changed[current_file].update(lines)

    return changed
