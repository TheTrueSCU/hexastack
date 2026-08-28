"""Test parity checker command."""

from __future__ import annotations

import sys

from scripts.pre_commit.check_test_parity import main as _main


def main() -> None:
    """CLI entrypoint for check-test-parity."""
    sys.exit(_main())


__all__ = [
    "main",
]
