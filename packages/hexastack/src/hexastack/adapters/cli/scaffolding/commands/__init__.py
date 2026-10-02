"""CLI scaffolding commands module initializer.

Notes/Architectural Intent:
    Serves strictly as a public API export boundary without operational logic,
    re-exporting commands and registration utilities from underlying modules.
"""

from __future__ import annotations

from hexastack.adapters.cli.scaffolding.commands.init import add_init_command
from hexastack.adapters.cli.scaffolding.commands.new import create_new_app
from hexastack.adapters.cli.scaffolding.commands.registration import (
    add_scaffold_commands,
)

__all__ = [
    "add_init_command",
    "add_scaffold_commands",
    "create_new_app",
]
