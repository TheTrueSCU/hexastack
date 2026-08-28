"""Deptry dependency tree auditor command."""

from __future__ import annotations

import sys

from scripts.deptry.run import main as _main


def main() -> None:
    """CLI entrypoint for deptry-run."""
    sys.exit(_main())


__all__ = [
    "main",
]
