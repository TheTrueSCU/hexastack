"""Unit tests for governance infrastructure bootstrapping.

Notes/Architectural Intent:
    Verifies that create_governance_bus instantiates SynchronousCommandBus, registers
    all governance command handlers, and enables end-to-end command dispatching.
"""

from pathlib import Path
from unittest.mock import MagicMock

from hexastack_tools.domain.governance import (
    CheckResult,
    CheckStatus,
    RunLinterCommand,
    RunSanityCheckCommand,
    SanityCheckReport,
    SanityTarget,
)
from hexastack_tools.infra.bootstrap import create_governance_bus
from hexastack_tools.ports.governance import ToolRunnerPort


def test_create_governance_bus_wires_and_dispatches():
    """Verify that create_governance_bus correctly wires commands to handlers."""
    mock_runner = MagicMock(spec=ToolRunnerPort)
    mock_runner.run_ruff.return_value = CheckResult(
        "Ruff", "test-pkg", CheckStatus.PASS, 0.05
    )
    mock_runner.run_ty.return_value = CheckResult(
        "Ty", "test-pkg", CheckStatus.PASS, 0.05
    )
    mock_runner.run_complexipy.return_value = CheckResult(
        "Complexity", "test-pkg", CheckStatus.PASS, 0.05
    )
    mock_runner.run_all_statements.return_value = CheckResult(
        "AllStatements", "test-pkg", CheckStatus.PASS, 0.05
    )
    mock_runner.run_test_parity.return_value = CheckResult(
        "Parity", "test-pkg", CheckStatus.PASS, 0.05
    )
    mock_runner.run_pytest.return_value = CheckResult(
        "Pytest", "test-pkg", CheckStatus.PASS, 0.05
    )

    bus = create_governance_bus(runner=mock_runner)

    # 1. Test dispatching a single command
    linter_cmd = RunLinterCommand(paths=(Path(),), target_name="test-pkg")
    linter_res = bus.dispatch(linter_cmd)
    assert isinstance(linter_res, CheckResult)
    assert linter_res.check_name == "Ruff"

    # 2. Test dispatching composite sanity command
    target = SanityTarget(
        name="test-pkg",
        kind="package",
        path=Path("/tmp/pkg"),
        src_paths=(Path("/tmp/pkg/src"),),
        test_paths=(Path("/tmp/pkg/tests"),),
    )
    sanity_cmd = RunSanityCheckCommand(
        targets=(target,),
        repo_root=Path("/tmp"),
    )
    report = bus.dispatch(sanity_cmd)
    assert isinstance(report, SanityCheckReport)
    assert report.exit_code == 0
    assert len(report.results) == 6
