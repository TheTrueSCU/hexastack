"""Unit tests for dependency auditing ports.

Notes/Architectural Intent:
    Verifies that DependencyAuditorPort and DependencyPresenterPort enforce
    abstract method signatures and prevent direct instantiation.
"""

from pathlib import Path

import pytest

from hexastack_tools.domain.dependencies import (
    DeptryAuditReport,
    DeptryPackageResult,
    ExtrasAuditResult,
    ImportLinterPackageResult,
    ImportLinterReport,
    UnifiedDependencyAuditReport,
)
from hexastack_tools.ports.dependencies import (
    DependencyAuditorPort,
    DependencyPresenterPort,
)


def test_dependency_ports_are_abstract():
    """Verify ports cannot be instantiated without implementations."""
    with pytest.raises(TypeError):
        DependencyAuditorPort()  # type: ignore[abstract]

    with pytest.raises(TypeError):
        DependencyPresenterPort()  # type: ignore[abstract]


def test_concrete_dependency_auditor_port(tmp_path: Path):
    """Verify concrete auditor satisfies the contract."""

    class DummyAuditor(DependencyAuditorPort):
        def audit_extras_parity(self, repo_root: Path) -> ExtrasAuditResult:
            return ExtrasAuditResult(violations=(), total_packages_checked=1)

        def generate_extras_diagram(self, repo_root: Path) -> str:
            return "graph LR"

        def run_deptry(self, pkg_dir: Path) -> DeptryPackageResult:
            return DeptryPackageResult(package_name=pkg_dir.name, passed=True)

        def run_import_linter(self, pkg_dir: Path) -> ImportLinterPackageResult:
            return ImportLinterPackageResult(package_name=pkg_dir.name, passed=True)

        def generate_import_linter_config(self, pkg_dir: Path) -> bool:
            return True

        def generate_architecture_diagrams(self, repo_root: Path) -> None:
            pass

        def check_tool_availability(
            self, import_name: str, cli_command: str | None = None
        ) -> tuple[bool, str]:
            return True, ""

    auditor = DummyAuditor()
    res = auditor.audit_extras_parity(tmp_path)
    assert res.is_healthy is True
    assert auditor.generate_extras_diagram(tmp_path) == "graph LR"


def test_concrete_dependency_presenter_port():
    """Verify concrete presenter satisfies the contract."""

    class DummyPresenter(DependencyPresenterPort):
        def present_extras_parity(
            self, result: ExtrasAuditResult, diagram: str | None = None
        ) -> int:
            return 0

        def present_deptry_audit(self, report: DeptryAuditReport) -> int:
            return report.exit_code

        def present_import_linter(self, report: ImportLinterReport) -> int:
            return report.exit_code

        def present_unified_deps_audit(
            self, report: UnifiedDependencyAuditReport
        ) -> int:
            return 0 if report.is_healthy else 1

    presenter = DummyPresenter()
    r1 = ExtrasAuditResult(violations=(), total_packages_checked=0)
    assert presenter.present_extras_parity(r1) == 0

    r2 = DeptryAuditReport(results=(), exit_code=0)
    assert presenter.present_deptry_audit(r2) == 0

    r3 = ImportLinterReport(results=(), exit_code=0)
    assert presenter.present_import_linter(r3) == 0

    r4 = UnifiedDependencyAuditReport(items=(), errors=(), is_healthy=True)
    assert presenter.present_unified_deps_audit(r4) == 0
