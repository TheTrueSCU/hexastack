"""Unit tests for all_statements command."""

from hexastack_tools.commands.all_statements import (
    check_main,
    fix_main,
)


def test_all_statements_callables_exist() -> None:
    """Verify callables are importable and defined."""
    assert callable(check_main)
    assert callable(fix_main)
