"""Rope AST manipulation and batch alphabetization commands."""

from __future__ import annotations

import sys

from scripts.rope.alphabetizer import main as _alpha_main
from scripts.rope.run import main as _run_main


def alphabetize_main() -> None:
    """CLI entrypoint for alphabetizer and rope-alphabetizer."""
    sys.exit(_alpha_main())


def run_main() -> None:
    """CLI entrypoint for rope-run."""
    sys.exit(_run_main())


__all__ = [
    "alphabetize_main",
    "run_main",
]
