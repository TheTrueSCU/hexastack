"""Unit tests for the performance tooling CLI command group.

Notes/Architectural Intent:
    Verifies that 'hexastack perf' correctly aggregates subcommands (load, profile, bench),
    forwards flags appropriately, and properly handles error conditions.
"""

from __future__ import annotations

from unittest.mock import patch

import typer
from typer.testing import CliRunner

from hexastack.adapters.cli.devtools.commands.perf import add_perf_commands


def test_perf_command_group_help() -> None:
    """Verify 'perf' help lists load, profile, and bench subcommands.

    Notes/Architectural Intent:
        Validates CLI taxonomy discoverability.
    """
    app = typer.Typer()
    add_perf_commands(app)
    runner = CliRunner()

    res = runner.invoke(app, ["perf", "--help"])
    assert res.exit_code == 0
    assert "load" in res.output
    assert "profile" in res.output
    assert "bench" in res.output


def test_perf_bench_command_delegation() -> None:
    """Verify 'perf bench' forwards execution arguments to pytest runner adapter.

    Notes/Architectural Intent:
        Ensures CLI delegation layer preserves arguments and handles non-zero exit codes.
    """
    app = typer.Typer()
    add_perf_commands(app)
    runner = CliRunner()

    with patch(
        "hexaqual.adapters.code_analysis.pytest_runner.run_main", return_value=0
    ) as mock_run:
        res = runner.invoke(app, ["perf", "bench", "-p", "hexastack-cqrs", "--smoke"])
        assert res.exit_code == 0
        assert mock_run.called
        call_argv = mock_run.call_args[0][0]
        assert "--bench" in call_argv
        assert "-p" in call_argv
        assert "hexastack-cqrs" in call_argv
        assert "--smoke" in call_argv


def test_perf_bench_command_failure() -> None:
    """Verify 'perf bench' raises typer.Exit on non-zero exit code.

    Notes/Architectural Intent:
        Prevents failing benchmarks from exiting with misleading 0 status.
    """
    app = typer.Typer()
    add_perf_commands(app)
    runner = CliRunner()

    with patch(
        "hexaqual.adapters.code_analysis.pytest_runner.run_main", return_value=1
    ):
        res = runner.invoke(app, ["perf", "bench", "-p", "hexastack-cqrs"])
        assert res.exit_code == 1
