"""Unit tests for test_parity command.

Notes/Architectural Intent:
    Verifies that test_parity CLI entrypoint delegates to presenter ports
    and properly handles arguments and return codes.
"""

from unittest.mock import MagicMock, patch

from hexastack_tools.commands.test_parity import main
from hexastack_tools.ports.governance import GovernancePresenterPort


def test_test_parity_main_callable() -> None:
    """Verify test parity main callable."""
    assert callable(main)


def test_test_parity_main_with_presenter(tmp_path) -> None:
    """Verify main delegates to presenter with parsed format."""
    mock_presenter = MagicMock(spec=GovernancePresenterPort)
    mock_presenter.present_test_parity.return_value = 0

    with (
        patch("sys.argv", ["check-test-parity", "--format", "json"]),
        patch(
            "hexastack_tools.commands.test_parity.get_repo_root",
            return_value=tmp_path,
        ),
        patch(
            "hexastack_tools.commands.test_parity.check_test_directories_inits",
            return_value=[],
        ),
        patch(
            "hexastack_tools.commands.test_parity.check_src_to_test_symmetry",
            return_value=[],
        ),
    ):
        code = main(presenter=mock_presenter)
        assert code == 0
        mock_presenter.present_test_parity.assert_called_once_with([], [])
