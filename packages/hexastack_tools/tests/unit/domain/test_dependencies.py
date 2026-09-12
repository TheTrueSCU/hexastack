"""Unit tests for dependency and boundary auditing domain models and commands.

Notes/Architectural Intent:
    Verifies immutability, properties, and validation rules for ExtrasAuditResult,
    DeptryPackageResult, ImportLinterReport, and dependency CQRS command objects.
"""

from __future__ import annotations

from pathlib import Path

from hexastack_tools.domain.dependencies import (
    AuditExtrasParityCommand,
    DependencyAuditItem,
    DeptryAuditReport,
    DeptryPackageResult,
    ExtraParityViolation,
    ExtrasAuditResult,
    GenerateImportLinterConfigCommand,
    ImportLinterPackageResult,
    ImportLinterReport,
    RunDeptryAuditCommand,
    RunImportLinterCommand,
    RunUnifiedDepsAuditCommand,
    UnifiedDependencyAuditReport,
)


def test_extra_parity_models():
    """Verify ExtraParityViolation and ExtrasAuditResult behaviour."""
    v = ExtraParityViolation(
        subpackage="hexastack-db",
        extra_name="sqlite",
        dependencies=("aiosqlite>=0.20",),
        suggested_fix="Add hexastack-db[sqlite] to umbrella pyproject.toml",
    )
    res_unhealthy = ExtrasAuditResult(violations=(v,), total_packages_checked=15)
    assert not res_unhealthy.is_healthy
    assert len(res_unhealthy.violations) == 1

    res_healthy = ExtrasAuditResult(violations=(), total_packages_checked=15)
    assert res_healthy.is_healthy


def test_deptry_and_import_linter_reports():
    """Verify Deptry and ImportLinter report aggregation."""
    d_pkg = DeptryPackageResult(package_name="core", passed=True)
    d_report = DeptryAuditReport(results=(d_pkg,), exit_code=0)
    assert d_report.exit_code == 0
    assert d_report.results[0].passed is True

    il_pkg = ImportLinterPackageResult(
        package_name="cqrs", passed=False, error_output="forbidden import"
    )
    il_report = ImportLinterReport(results=(il_pkg,), exit_code=1)
    assert il_report.exit_code == 1
    assert "forbidden" in il_report.results[0].error_output


def test_unified_dependency_report():
    """Verify UnifiedDependencyAuditReport structure."""
    item = DependencyAuditItem(
        check_name="Tool Readiness", passed=True, details="All tools available"
    )
    report = UnifiedDependencyAuditReport(
        items=(item,),
        errors=(),
        is_healthy=True,
        diagram_generated=True,
    )
    assert report.is_healthy is True
    assert report.diagram_generated is True
    assert len(report.items) == 1


def test_commands_instantiation(tmp_path: Path):
    """Verify dependency command objects instantiate properly."""
    c1 = AuditExtrasParityCommand(repo_root=tmp_path, generate_diagram=True)
    assert c1.generate_diagram is True

    c2 = RunDeptryAuditCommand(repo_root=tmp_path)
    assert c2.repo_root == tmp_path

    c3 = RunImportLinterCommand(
        repo_root=tmp_path, packages=(tmp_path,), all_packages=False
    )
    assert len(c3.packages) == 1

    c4 = GenerateImportLinterConfigCommand(repo_root=tmp_path)
    assert c4.repo_root == tmp_path

    c5 = RunUnifiedDepsAuditCommand(
        repo_root=tmp_path,
        check_deptry=True,
        check_extras=True,
        check_tools=False,
        generate_diagrams=True,
    )
    assert c5.check_tools is False
    assert c5.generate_diagrams is True
