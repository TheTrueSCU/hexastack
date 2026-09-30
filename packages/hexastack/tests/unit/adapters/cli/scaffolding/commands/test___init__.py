"""Unit tests for scaffolding commands module exports.

Notes/Architectural Intent:
    Verifies that scaffolding commands root initializer properly re-exports
    all public interface symbols.
"""

import hexastack.adapters.cli.scaffolding.commands as commands_mod


def test_scaffolding_commands_exports():
    """Verify scaffolding commands module defines expected __all__ exports."""
    all_exports = commands_mod.__all__
    assert "add_init_command" in all_exports
    assert "add_scaffold_commands" in all_exports
    assert "create_new_app" in all_exports
    assert callable(commands_mod.add_scaffold_commands)
