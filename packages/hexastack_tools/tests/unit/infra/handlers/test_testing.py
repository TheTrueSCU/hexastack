"""Unit tests for testing command handlers.

Notes/Architectural Intent:
    Verifies that mutation, boundary, redundancy, and test impact handlers
    delegate correctly to TestingRunnerPort and produce valid domain reports.
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

from hexastack_tools.domain.testing import (
    AuditTestBoundariesCommand,
    AuditTestRedundancyCommand,
    InspectMutationCacheCommand,
    RunImpactedTestsCommand,
    RunMutationTestsCommand,
)
from hexastack_tools.infra.handlers.testing import (
    AuditTestBoundariesHandler,
    AuditTestRedundancyHandler,
    InspectMutationCacheHandler,
    RunImpactedTestsHandler,
    RunMutationTestsHandler,
)
from hexastack_tools.ports.testing import TestingRunnerPort


def test_run_mutation_tests_handler(tmp_path: Path):
    """Verify RunMutationTestsHandler delegates to runner."""
    runner = MagicMock(spec=TestingRunnerPort)
    runner.run_mutmut.return_value = 0
    handler = RunMutationTestsHandler(runner)

    with patch(
        "hexastack_tools.infra.handlers.testing.get_package_directory",
        return_value=tmp_path,
    ):
        code = handler.handle(RunMutationTestsCommand(package="core", reset_cache=True))
        assert code == 0
        runner.run_mutmut.assert_called_once_with(tmp_path, reset_cache=True)


def test_inspect_mutation_cache_handler(tmp_path: Path):
    """Verify InspectMutationCacheHandler aggregates records and categorizes."""
    runner = MagicMock(spec=TestingRunnerPort)
    runner.read_mutmut_cache.return_value = [
        {
            "id": "1",
            "filename": "packages/core/src/service.py",
            "line": "if status == 1:",
            "status": "bad_survived",
        }
    ]
    handler = InspectMutationCacheHandler(runner)

    cmd = InspectMutationCacheCommand(
        cache_file=tmp_path / ".mutmut-cache",
        actionable_only=True,
    )
    report = handler.handle(cmd)
    assert len(report.summaries) == 1
    assert report.total_critical == 1
    assert len(report.actionable_mutants) == 1


def test_audit_test_boundaries_handler(tmp_path: Path):
    """Verify AuditTestBoundariesHandler constructs report."""
    runner = MagicMock(spec=TestingRunnerPort)
    runner.audit_layer_boundary_leaks.return_value = [("test_domain", "infra.py")]
    handler = AuditTestBoundariesHandler(runner)

    cmd = AuditTestBoundariesCommand(coverage_file=tmp_path / ".coverage")
    report = handler.handle(cmd)
    assert report.is_healthy is False
    assert len(report.leaks) == 1


def test_audit_test_redundancy_handler(tmp_path: Path):
    """Verify AuditTestRedundancyHandler constructs report."""
    runner = MagicMock(spec=TestingRunnerPort)
    runner.audit_redundant_tests.return_value = ["test_dup"]
    handler = AuditTestRedundancyHandler(runner)

    cmd = AuditTestRedundancyCommand(coverage_file=tmp_path / ".coverage")
    report = handler.handle(cmd)
    assert report.redundant_tests == ("test_dup",)


def test_run_impacted_tests_handler_dry_run(tmp_path: Path):
    """Verify RunImpactedTestsHandler in dry-run mode."""
    runner = MagicMock(spec=TestingRunnerPort)
    file_path = tmp_path / "src/app.py"
    runner.get_changed_lines.return_value = {file_path: {10}}
    runner.find_impacted_tests.return_value = {"tests/test_app.py::test_run"}
    handler = RunImpactedTestsHandler(runner)

    cmd = RunImpactedTestsCommand(
        repo_root=tmp_path,
        dry_run=True,
    )
    report = handler.handle(cmd)
    assert report.dry_run is True
    assert len(report.impacted_tests) == 1
    runner.execute_pytest.assert_not_called()
