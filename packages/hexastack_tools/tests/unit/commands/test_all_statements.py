"""Unit tests for all_statements command.

Notes/Architectural Intent:
    Verifies that all_statements CLI entrypoints delegate to presenter ports
    and properly handle arguments and return codes.
"""

from unittest.mock import MagicMock, patch

from hexastack_tools.commands.all_statements import (
    check_main,
    fix_main,
    main_check,
    main_fix,
)
from hexastack_tools.ports.governance import GovernancePresenterPort


def test_all_statements_callables_exist() -> None:
    """Verify callables are importable and defined."""
    assert callable(check_main)
    assert callable(fix_main)


def test_main_check_with_presenter() -> None:
    """Verify main_check delegates to presenter."""
    mock_presenter = MagicMock(spec=GovernancePresenterPort)
    mock_presenter.present_all_statements.return_value = 0

    with (
        patch("sys.argv", ["check-all-statements", "--format", "json"]),
        patch(
            "hexastack_tools.commands.all_statements.resolve_target_python_files",
            return_value=[],
        ),
    ):
        code = main_check(presenter=mock_presenter)
        assert code == 0
        mock_presenter.present_all_statements.assert_called_once_with([])


def test_main_fix_with_presenter() -> None:
    """Verify main_fix delegates to presenter."""
    mock_presenter = MagicMock(spec=GovernancePresenterPort)

    with (
        patch("sys.argv", ["fix-all-statements", "--format", "markdown"]),
        patch(
            "hexastack_tools.commands.all_statements.resolve_target_python_files",
            return_value=[],
        ),
    ):
        main_fix(presenter=mock_presenter)
        mock_presenter.present_all_statements.assert_called_once_with(
            [], modified_count=0
        )
