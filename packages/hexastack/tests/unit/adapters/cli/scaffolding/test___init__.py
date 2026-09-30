"""Unit tests for scaffolding CLI adapter initializer.

Notes/Architectural Intent:
    Verifies that scaffolding package root initializer properly re-exports
    all public interface symbols.
"""

import hexastack.adapters.cli.scaffolding as scaffolding_mod


def test_scaffolding_exports():
    """Verify scaffolding module defines expected __all__ exports."""
    all_exports = scaffolding_mod.__all__
    assert "add_init_command" in all_exports
    assert "add_scaffold_commands" in all_exports
    assert "create_new_app" in all_exports
    assert callable(scaffolding_mod.add_scaffold_commands)
