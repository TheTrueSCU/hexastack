"""CLI main execution entrypoint in infrastructure layer."""

from __future__ import annotations

import sys
from financial_ledger.infra.bootstrap import create_app

__all__ = [
    "main",
]


def main() -> None:
    """CLI entrypoint."""
    app = create_app()
    cli_app = app.get("cli_app")
    if cli_app is not None:
        cli_app()
    else:
        sys.stderr.write("CLI application failed to bootstrap.\n")
        sys.exit(1)
