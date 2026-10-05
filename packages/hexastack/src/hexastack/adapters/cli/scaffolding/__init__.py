"""CLI scaffolding module initializer.

Notes/Architectural Intent:
    Serves strictly as a public API export boundary without operational logic,
    re-exporting scaffolding commands and creation utilities.
"""

from __future__ import annotations

from hexastack.adapters.cli.scaffolding.commands import (
    add_init_command,
    add_scaffold_commands,
    create_new_app,
)

__all__ = [
    "add_init_command",
    "add_scaffold_commands",
    "create_new_app",
]
