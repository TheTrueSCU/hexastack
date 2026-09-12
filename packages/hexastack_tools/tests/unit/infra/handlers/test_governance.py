"""Unit tests for governance CQRS command handlers.

Notes/Architectural Intent:
    Verifies that leaf handlers invoke their respective ToolRunnerPort methods,
    and that RunSanityCheckHandler dispatches each sub-command through the bus.
"""

from pathlib import Path
from unittest.mock import MagicMock

from hexastack_cqrs.ports.buses import CommandBusPort
from hexastack_tools.domain.governance import (
    AuditComplexityCommand,
    CheckAllStatementsCommand,
    CheckResult,
    CheckStatus,
    CheckTestParityCommand,
    RunLinterCommand,
    RunPytestCommand,
    RunSanityCheckCommand,
    RunTypecheckCommand,
    SanityTarget,
)
from hexastack_tools.infra.handlers.governance import (
    AuditComplexityHandler,
    CheckAllStatementsHandler,
    CheckTestParityHandler,
    RunLinterHandler,
    RunPytestHandler,
    RunSanityCheckHandler,
    RunTypecheckHandler,
)
from hexastack_tools.ports.governance import ToolRunnerPort


def test_leaf_governance_handlers():
    """Verify each leaf handler delegates to the matching ToolRunnerPort method."""
    mock_runner = MagicMock(spec=ToolRunnerPort)
    expected_res = CheckResult("Dummy", "pkg", CheckStatus.PASS, 0.05)
    mock_runner.run_ruff.return_value = expected_res
    mock_runner.run_ty.return_value = expected_res
    mock_runner.run_complexipy.return_value = expected_res
    mock_runner.run_all_statements.return_value = expected_res
    mock_runner.run_test_parity.return_value = expected_res
    mock_runner.run_pytest.return_value = expected_res

    target = SanityTarget("cqrs", "package", Path("/tmp"), (Path("/tmp"),), ())

    h_lint = RunLinterHandler(mock_runner)
    assert (
        h_lint.handle(RunLinterCommand(paths=(Path(),), target_name="cqrs", fix=True))
        == expected_res
    )
    mock_runner.run_ruff.assert_called_once()

    h_ty = RunTypecheckHandler(mock_runner)
    assert (
        h_ty.handle(RunTypecheckCommand(paths=(Path(),), target_name="cqrs"))
        == expected_res
    )
    mock_runner.run_ty.assert_called_once()

    h_cpx = AuditComplexityHandler(mock_runner)
    assert (
        h_cpx.handle(
            AuditComplexityCommand(
                paths=(Path(),), target_name="cqrs", max_complexity=25
            )
        )
        == expected_res
    )
    mock_runner.run_complexipy.assert_called_once()

    h_all = CheckAllStatementsHandler(mock_runner)
    assert (
        h_all.handle(CheckAllStatementsCommand(paths=(Path(),), target_name="cqrs"))
        == expected_res
    )
    mock_runner.run_all_statements.assert_called_once()

    h_parity = CheckTestParityHandler(mock_runner)
    assert (
        h_parity.handle(CheckTestParityCommand(target=target, repo_root=Path("/tmp")))
        == expected_res
    )
    mock_runner.run_test_parity.assert_called_once()

    h_pytest = RunPytestHandler(mock_runner)
    assert (
        h_pytest.handle(
            RunPytestCommand(target=target, repo_root=Path("/tmp"), skip=True)
        )
        == expected_res
    )
    mock_runner.run_pytest.assert_called_once()


def test_run_sanity_check_handler_composite_dispatch():
    """Verify RunSanityCheckHandler dispatches sub-commands through CommandBusPort."""
    mock_bus = MagicMock(spec=CommandBusPort)
    pass_res = CheckResult("SubCheck", "target", CheckStatus.PASS, 0.01)
    mock_bus.dispatch.return_value = pass_res

    handler = RunSanityCheckHandler(mock_bus)
    pkg_target = SanityTarget(
        name="cqrs",
        kind="package",
        path=Path("/tmp/cqrs"),
        src_paths=(Path("/tmp/cqrs/src"),),
        test_paths=(Path("/tmp/cqrs/tests"),),
    )
    cmd = RunSanityCheckCommand(
        targets=(pkg_target,),
        repo_root=Path("/tmp"),
        fix=False,
        skip_tests=False,
        max_complexity=25,
    )

    report = handler.handle(cmd)
    assert report.exit_code == 0
    # Package target should dispatch: linter, ty, complexipy, all_statements, parity, pytest = 6 calls
    assert mock_bus.dispatch.call_count == 6
    assert len(report.results) == 6


def test_run_sanity_check_handler_with_failures():
    """Verify RunSanityCheckHandler sets exit_code=1 on any check failure."""
    mock_bus = MagicMock(spec=CommandBusPort)
    fail_res = CheckResult("Linter", "target", CheckStatus.FAIL, 0.05, "error")
    mock_bus.dispatch.return_value = fail_res

    handler = RunSanityCheckHandler(mock_bus)
    target = SanityTarget("file.py", "file", Path("file.py"), (Path("file.py"),), ())
    cmd = RunSanityCheckCommand(
        targets=(target,),
        repo_root=Path("/tmp"),
    )

    report = handler.handle(cmd)
    assert report.exit_code == 1
    assert any(r.status == CheckStatus.FAIL for r in report.results)
