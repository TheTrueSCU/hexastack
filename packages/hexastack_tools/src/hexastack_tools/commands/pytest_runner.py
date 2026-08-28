"""Pytest test runner and architecture contract generator commands."""

from __future__ import annotations

import sys

from scripts.pytest.run import main as _run_main
from scripts.pytest_archon.generate import main as _archon_main


def archon_generate_main() -> None:
    """CLI entrypoint for pytest-archon-generate."""
    sys.exit(_archon_main())


def run_main() -> None:
    """CLI entrypoint for pytest-run."""
    sys.exit(_run_main())


__all__ = [
    "archon_generate_main",
    "run_main",
]
