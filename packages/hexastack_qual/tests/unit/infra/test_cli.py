"""Unit tests for hexastack-qual Typer CLI.

Notes/Architectural Intent:
    Verifies that the qual CLI subcommands (check, format, mcp) invoke the
    underlying HexaqualRunnerAdapter and MCP server runners with correct
    arguments and exit codes.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import hexastack_qual.infra.cli as cli_module
from hexastack_qual.domain.models import QualityCheckResult, QualityScorecard
from hexastack_qual.infra.cli import app
from typer.testing import CliRunner

runner = CliRunner()


def test_cli_check_healthy():
    """Verify check subcommand exits 0 when all sanity checks pass."""
    mock_runner = MagicMock()
    mock_runner.run_sanity.return_value = QualityScorecard(
        target="workspace",
        is_healthy=True,
        checks=[
            QualityCheckResult(
                check_name="ruff", target="workspace", status="pass", details="ok"
            ),
            QualityCheckResult(
                check_name="ty", target="workspace", status="pass", details="ok"
            ),
        ],
    )

    with patch.object(cli_module, "HexaqualRunnerAdapter", return_value=mock_runner):
        result = runner.invoke(app, ["check"])

    assert result.exit_code == 0
    assert "✅ ruff: ok" in result.stdout
    assert "✅ ty: ok" in result.stdout
    mock_runner.run_sanity.assert_called_once_with(package=None, skip_tests=True)


def test_cli_check_unhealthy():
    """Verify check subcommand exits 1 when sanity checks fail."""
    mock_runner = MagicMock()
    mock_runner.run_sanity.return_value = QualityScorecard(
        target="core",
        is_healthy=False,
        checks=[
            QualityCheckResult(
                check_name="ruff", target="core", status="fail", details="syntax error"
            ),
        ],
    )

    with patch.object(cli_module, "HexaqualRunnerAdapter", return_value=mock_runner):
        result = runner.invoke(app, ["check", "-p", "core", "--no-skip-tests"])

    assert result.exit_code == 1
    assert "❌ ruff: syntax error" in result.stdout
    mock_runner.run_sanity.assert_called_once_with(package="core", skip_tests=False)


def test_cli_format_statements():
    """Verify format subcommand invokes fix_statements and outputs count."""
    mock_runner = MagicMock()
    mock_runner.fix_statements.return_value = 5

    with patch.object(cli_module, "HexaqualRunnerAdapter", return_value=mock_runner):
        result = runner.invoke(app, ["format", "-p", "cqrs"])

    assert result.exit_code == 0
    assert "5 file(s)" in result.stdout
    mock_runner.fix_statements.assert_called_once_with(package="cqrs")


def test_cli_serve_mcp():
    """Verify mcp subcommand invokes run_quality_mcp_server."""
    mock_run_server = AsyncMock()

    with patch(
        "hexastack_qual.adapters.mcp.server.run_quality_mcp_server", mock_run_server
    ):
        result = runner.invoke(app, ["mcp"])

    assert result.exit_code == 0
    mock_run_server.assert_called_once()
