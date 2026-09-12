"""Unit tests for dependency command handlers.

Notes/Architectural Intent:
    Verifies that handlers delegate to DependencyAuditorPort and produce
    valid domain reports with accurate exit codes and diagnostic aggregations.
"""

from pathlib import Path
from unittest.mock import MagicMock, patch

from hexastack_tools.domain.dependencies import (
    AuditExtrasParityCommand,
    DeptryPackageResult,
    ExtrasAuditResult,
    GenerateImportLinterConfigCommand,
    ImportLinterPackageResult,
    RunDeptryAuditCommand,
    RunImportLinterCommand,
    RunUnifiedDepsAuditCommand,
)
from hexastack_tools.infra.handlers.dependencies import (
    AuditExtrasParityHandler,
    GenerateImportLinterConfigHandler,
    RunDeptryAuditHandler,
    RunImportLinterHandler,
    RunUnifiedDepsAuditHandler,
)
from hexastack_tools.ports.dependencies import DependencyAuditorPort


def test_audit_extras_parity_handler(tmp_path: Path):
    """Verify AuditExtrasParityHandler delegates to auditor."""
    auditor = MagicMock(spec=DependencyAuditorPort)
    handler = AuditExtrasParityHandler(auditor)

    # 1. Normal audit
    auditor.audit_extras_parity.return_value = ExtrasAuditResult(
        violations=(), total_packages_checked=1
    )
    res = handler.handle(
        AuditExtrasParityCommand(repo_root=tmp_path, generate_diagram=False)
    )
    assert res.is_healthy is True

    # 2. Diagram generation
    auditor.generate_extras_diagram.return_value = "graph LR"
    diagram = handler.handle(
        AuditExtrasParityCommand(repo_root=tmp_path, generate_diagram=True)
    )
    assert diagram == "graph LR"


def test_run_deptry_audit_handler(tmp_path: Path):
    """Verify RunDeptryAuditHandler aggregates results and computes exit code."""
    auditor = MagicMock(spec=DependencyAuditorPort)
    handler = RunDeptryAuditHandler(auditor)

    auditor.run_deptry.return_value = DeptryPackageResult(
        package_name="core", passed=True
    )
    with patch(
        "hexastack_tools.infra.handlers.dependencies.get_package_directories",
        return_value=[tmp_path],
    ):
        report = handler.handle(RunDeptryAuditCommand(repo_root=tmp_path))
        assert report.exit_code == 0
        assert len(report.results) == 1

        # Failure case
        auditor.run_deptry.return_value = DeptryPackageResult(
            package_name="core", passed=False, error_output="err"
        )
        report_fail = handler.handle(RunDeptryAuditCommand(repo_root=tmp_path))
        assert report_fail.exit_code == 1


def test_run_import_linter_handler(tmp_path: Path):
    """Verify RunImportLinterHandler evaluates contracts."""
    auditor = MagicMock(spec=DependencyAuditorPort)
    handler = RunImportLinterHandler(auditor)

    auditor.run_import_linter.return_value = ImportLinterPackageResult(
        package_name="core", passed=True
    )
    report = handler.handle(
        RunImportLinterCommand(repo_root=tmp_path, packages=(tmp_path,))
    )
    assert report.exit_code == 0


def test_generate_import_linter_config_handler(tmp_path: Path):
    """Verify GenerateImportLinterConfigHandler triggers config updates."""
    auditor = MagicMock(spec=DependencyAuditorPort)
    handler = GenerateImportLinterConfigHandler(auditor)

    auditor.generate_import_linter_config.return_value = True
    assert (
        handler.handle(
            GenerateImportLinterConfigCommand(repo_root=tmp_path, packages=(tmp_path,))
        )
        is True
    )


def test_run_unified_deps_audit_handler(tmp_path: Path):
    """Verify RunUnifiedDepsAuditHandler coordinates tools, extras, deptry, diagrams."""
    auditor = MagicMock(spec=DependencyAuditorPort)
    handler = RunUnifiedDepsAuditHandler(auditor)

    auditor.check_tool_availability.return_value = (True, "")
    auditor.audit_extras_parity.return_value = ExtrasAuditResult(
        violations=(), total_packages_checked=1
    )
    auditor.run_deptry.return_value = DeptryPackageResult("core", True)

    with patch(
        "hexastack_tools.infra.handlers.dependencies.get_package_directories",
        return_value=[tmp_path],
    ):
        report = handler.handle(
            RunUnifiedDepsAuditCommand(
                repo_root=tmp_path,
                check_deptry=True,
                check_extras=True,
                check_tools=True,
                generate_diagrams=True,
            )
        )
        assert report.is_healthy is True
        assert report.diagram_generated is True
        assert len(report.items) == 3
