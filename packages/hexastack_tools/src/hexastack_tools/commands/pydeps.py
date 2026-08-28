"""Pydeps architecture dependency graph generator command."""

from __future__ import annotations

import sys

from scripts.pydeps.generate import main as _main


def generate_main() -> None:
    """CLI entrypoint for pydeps-generate."""
    sys.exit(_main())


__all__ = [
    "generate_main",
]
