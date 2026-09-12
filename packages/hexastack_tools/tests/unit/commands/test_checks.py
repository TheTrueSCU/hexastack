"""Unit tests for checks command."""

from unittest.mock import MagicMock, patch

import pytest
import typer

from hexastack_tools.adapters.presenters.checks import build_checks_table
from hexastack_tools.commands.checks import app, checks, main
from hexastack_tools.domain.github import CheckRunFinding, ChecksReport, OutputFormat


def test_format_checks_table() -> None:
    """Verify checks table format output."""
    check = CheckRunFinding(
        name="unit-tests",
        status="completed",
        conclusion="success",
        details_url="https://ci.example.com",
    )
    table = build_checks_table([check], "main")
    assert table.title is not None


def test_checks_command_callables() -> None:
    """Verify checks Typer app and callables."""
    assert callable(main)
    assert callable(checks)
    assert app is not None


def test_checks_command_execution() -> None:
    """Verify checks command dispatches to bus and invokes presenter."""
    mock_bus = MagicMock()
    mock_report = ChecksReport(ref_or_pr="123", check_runs=())
    mock_bus.dispatch.return_value = mock_report

    mock_presenter = MagicMock()
    mock_presenter.present_checks.return_value = 0

    with (
        patch(
            "hexastack_tools.commands.checks.create_governance_bus",
            return_value=mock_bus,
        ),
        patch(
            "hexastack_tools.commands.checks.create_github_presenter",
            return_value=mock_presenter,
        ),
    ):
        checks(ref_or_pr="123", output_format=OutputFormat.RICH)

    mock_bus.dispatch.assert_called_once()
    mock_presenter.present_checks.assert_called_once_with(mock_report)


def test_checks_command_failure_exit() -> None:
    """Verify checks command exits with code on presenter failure."""
    mock_bus = MagicMock()
    mock_presenter = MagicMock()
    mock_presenter.present_checks.return_value = 1

    with (
        patch(
            "hexastack_tools.commands.checks.create_governance_bus",
            return_value=mock_bus,
        ),
        patch(
            "hexastack_tools.commands.checks.create_github_presenter",
            return_value=mock_presenter,
        ),
    ):
        with pytest.raises(typer.Exit) as exc_info:
            checks(ref_or_pr="fail", output_format=OutputFormat.RICH)
        assert exc_info.value.exit_code == 1
