"""Unit tests for security command."""

from unittest.mock import MagicMock, patch

import pytest
import typer

from hexastack_tools.commands.security import app, main, security
from hexastack_tools.domain.github import OutputFormat, SecurityCommentsReport


def test_security_main_callable() -> None:
    """Verify security command main callable and app."""
    assert callable(main)
    assert callable(security)
    assert app is not None


def test_security_command_dispatches() -> None:
    """Verify security command dispatches InspectSecurityCommentsCommand to bus."""
    mock_bus = MagicMock()
    mock_report = SecurityCommentsReport(pr_number=42, threads=())
    mock_bus.dispatch.return_value = mock_report

    with (
        patch(
            "hexastack_tools.commands.security.create_governance_bus",
            return_value=mock_bus,
        ),
        patch(
            "hexastack_tools.commands.security.present_security_comments"
        ) as mock_present,
    ):
        security(pr_number=42, output_format=OutputFormat.RICH)

    mock_bus.dispatch.assert_called_once()
    mock_present.assert_called_once_with((), 42, output_format=OutputFormat.RICH)


def test_security_command_error_handling() -> None:
    """Verify security command raises typer.Exit on error."""
    mock_bus = MagicMock()
    mock_bus.dispatch.side_effect = RuntimeError("API failed")

    with patch(
        "hexastack_tools.commands.security.create_governance_bus",
        return_value=mock_bus,
    ):
        with pytest.raises(typer.Exit) as exc_info:
            security(pr_number=42)
        assert exc_info.value.exit_code == 1
