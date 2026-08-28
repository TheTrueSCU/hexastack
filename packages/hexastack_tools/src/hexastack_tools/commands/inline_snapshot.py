"""Inline snapshot updater command."""

from __future__ import annotations

import sys

from scripts.inline_snapshot.update import main as _main


def main() -> None:
    """CLI entrypoint for inline-snapshot-update."""
    sys.exit(_main())


__all__ = [
    "main",
]
