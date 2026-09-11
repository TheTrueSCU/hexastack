"""Unit tests for governance infrastructure bootstrapping.

Notes/Architectural Intent:
    Verifies that create_governance_bus instantiates SynchronousCommandBus, registers
    all governance command handlers, and enables end-to-end command dispatching.
"""

from pathlib import Path
from unittest.mock import MagicMock

from hexastack_tools.domain.dependencies import (
    AuditExtrasParityCommand,
    ExtrasAuditResult,
)
from hexastack_tools.domain.governance import (
    CheckResult,
    CheckStatus,
    RunLinterCommand,
    RunSanityCheckCommand,
    SanityCheckReport,
    SanityTarget,
)
from hexastack_tools.domain.testing import (
    AuditTestBoundariesCommand,
    AuditTestRedundancyCommand,
    BoundaryAuditReport,
    ImpactedTestsReport,
    InspectMutationCacheCommand,
    MutationAuditReport,
    RedundancyAuditReport,
    RunImpactedTestsCommand,
    RunMutationTestsCommand,
)
from hexastack_tools.infra.bootstrap import create_governance_bus
from hexastack_tools.ports.dependencies import DependencyAuditorPort
from hexastack_tools.ports.governance import ToolRunnerPort
from hexastack_tools.ports.testing import TestingRunnerPort


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

    mock_dep_auditor = MagicMock(spec=DependencyAuditorPort)
    mock_dep_auditor.audit_extras_parity.return_value = ExtrasAuditResult(
        violations=(),
        total_packages_checked=1,
    )

    mock_testing_runner = MagicMock(spec=TestingRunnerPort)
    mock_testing_runner.run_mutmut.return_value = 0
    mock_testing_runner.read_mutmut_cache.return_value = []
    mock_testing_runner.get_changed_lines.return_value = {}
    mock_testing_runner.find_impacted_tests.return_value = set()
    mock_testing_runner.get_tests_covering_line.return_value = []
    mock_testing_runner.audit_layer_boundary_leaks.return_value = []
    mock_testing_runner.audit_redundant_tests.return_value = []
    mock_testing_runner.execute_pytest.return_value = 0

    bus = create_governance_bus(
        runner=mock_runner,
        dependency_auditor=mock_dep_auditor,
        testing_runner=mock_testing_runner,
    )

    # 1. Test dispatching a single governance command
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

    # 3. Test dispatching dependency command
    extras_cmd = AuditExtrasParityCommand(repo_root=Path("/tmp"))
    extras_res = bus.dispatch(extras_cmd)
    assert isinstance(extras_res, ExtrasAuditResult)
    assert extras_res.is_healthy is True

    # 4. Test dispatching testing commands
    mutmut_res = bus.dispatch(RunMutationTestsCommand())
    assert mutmut_res == 0

    inspect_res = bus.dispatch(InspectMutationCacheCommand(package="core"))
    assert isinstance(inspect_res, MutationAuditReport)

    boundary_res = bus.dispatch(AuditTestBoundariesCommand())
    assert isinstance(boundary_res, BoundaryAuditReport)

    redundancy_res = bus.dispatch(AuditTestRedundancyCommand())
    assert isinstance(redundancy_res, RedundancyAuditReport)

    impact_res = bus.dispatch(RunImpactedTestsCommand())
    assert isinstance(impact_res, ImpactedTestsReport)
