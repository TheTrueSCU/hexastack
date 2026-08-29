"""Unit tests for import_linter commands."""

from hexastack_tools.commands.import_linter import (
    generate_main,
    run_main,
)


def test_import_linter_callables() -> None:
    """Verify import linter callables."""
    assert callable(generate_main)
    assert callable(run_main)
