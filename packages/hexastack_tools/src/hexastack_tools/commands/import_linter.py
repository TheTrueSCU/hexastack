"""Import linter commands for contract generation and evaluation."""

from __future__ import annotations

import sys

from scripts.import_linter.generate import main as _gen_main
from scripts.import_linter.run import main as _run_main


def generate_main() -> None:
    """CLI entrypoint for import-linter-generate."""
    sys.exit(_gen_main())


def run_main() -> None:
    """CLI entrypoint for import-linter-run."""
    sys.exit(_run_main())


__all__ = [
    "generate_main",
    "run_main",
]
