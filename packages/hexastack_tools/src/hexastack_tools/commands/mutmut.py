"""Mutmut mutation testing commands."""

from __future__ import annotations

import sys

from scripts.mutmut.inspect import main as _inspect_main
from scripts.mutmut.run import main as _run_main


def inspect_main() -> None:
    """CLI entrypoint for mutmut-inspect."""
    sys.exit(_inspect_main())


def run_main() -> None:
    """CLI entrypoint for mutmut-run."""
    sys.exit(_run_main())


__all__ = [
    "inspect_main",
    "run_main",
]
