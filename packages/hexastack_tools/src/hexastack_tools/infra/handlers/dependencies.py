"""Command handlers for dependency, optional extras, and architecture boundary auditing.

Notes/Architectural Intent:
    Implements CommandHandlerPort contracts for executing dependency checks,
    extras parity validation, import-linter contract checking, and unified auditing.
"""

from __future__ import annotations

from typing import Any

from hexastack_tools.domain.dependencies import (
    AuditExtrasParityCommand,
    DependencyAuditItem,
    DeptryAuditReport,
    DeptryPackageResult,
    GenerateImportLinterConfigCommand,
    ImportLinterPackageResult,
    ImportLinterReport,
    RunDeptryAuditCommand,
    RunImportLinterCommand,
    RunUnifiedDepsAuditCommand,
    UnifiedDependencyAuditReport,
)
from hexastack_tools.ports.dependencies import DependencyAuditorPort
from hexastack_tools.utils.workspace import get_package_directories

__all__ = [
    "AuditExtrasParityHandler",
    "GenerateImportLinterConfigHandler",
    "RunDeptryAuditHandler",
    "RunImportLinterHandler",
    "RunUnifiedDepsAuditHandler",
]

_EXPECTED_TOOLS: list[tuple[str, str, str | None]] = [
    ("importlinter", "governance (import-linter-run)", "lint-imports"),
    ("deptry", "governance (deptry-run)", "deptry"),
    ("mutmut", "mutmut (mutmut-run)", "mutmut"),
    ("pydeps", "diagrams (pydeps-generate)", "pydeps"),
    ("libcst", "rope (alphabetizer)", None),
    ("pytest_archon", "archon (pytest-archon-generate)", None),
    ("inline_snapshot", "snapshots (inline-snapshot-update)", None),
]


class AuditExtrasParityHandler:
    """Handler evaluating optional dependencies forwarding or generating Mermaid diagram."""

    def __init__(self, auditor: DependencyAuditorPort) -> None:
        """Initialize handler with DependencyAuditorPort adapter.

        Args:
            auditor: DependencyAuditorPort instance.
        """
        self._auditor = auditor

    def handle(self, command: AuditExtrasParityCommand) -> Any:
        """Execute extras parity audit or generate diagram.

        Args:
            command: AuditExtrasParityCommand instance.

        Returns:
            Mermaid string if generate_diagram is True, otherwise ExtrasAuditResult.
        """
        if command.generate_diagram:
            return self._auditor.generate_extras_diagram(command.repo_root)
        return self._auditor.audit_extras_parity(command.repo_root)


class RunDeptryAuditHandler:
    """Handler executing deptry dependency analysis across packages."""

    def __init__(self, auditor: DependencyAuditorPort) -> None:
        """Initialize handler with DependencyAuditorPort adapter.

        Args:
            auditor: DependencyAuditorPort instance.
        """
        self._auditor = auditor

    def handle(self, command: RunDeptryAuditCommand) -> DeptryAuditReport:
        """Audit source imports for all workspace packages.

        Args:
            command: RunDeptryAuditCommand instance.

        Returns:
            DeptryAuditReport domain model.
        """
        results: list[DeptryPackageResult] = []
        for pkg_dir in get_package_directories(command.repo_root):
            results.append(self._auditor.run_deptry(pkg_dir))

        exit_code = 1 if any(not r.passed for r in results) else 0
        return DeptryAuditReport(results=tuple(results), exit_code=exit_code)


class RunImportLinterHandler:
    """Handler executing hexagonal architecture contract verification with import-linter."""

    def __init__(self, auditor: DependencyAuditorPort) -> None:
        """Initialize handler with DependencyAuditorPort adapter.

        Args:
            auditor: DependencyAuditorPort instance.
        """
        self._auditor = auditor

    def handle(self, command: RunImportLinterCommand) -> ImportLinterReport:
        """Evaluate import contracts for targeted or all packages.

        Args:
            command: RunImportLinterCommand instance.

        Returns:
            ImportLinterReport domain model.
        """
        if command.packages:
            targets = list(command.packages)
        else:
            all_pkgs = get_package_directories(command.repo_root)
            targets = [p for p in all_pkgs if (p / "pyproject.toml").is_file()]

        results: list[ImportLinterPackageResult] = []
        for pkg in sorted(targets):
            results.append(self._auditor.run_import_linter(pkg))

        exit_code = 1 if any(not r.passed for r in results) else 0
        return ImportLinterReport(results=tuple(results), exit_code=exit_code)


class GenerateImportLinterConfigHandler:
    """Handler generating or updating [tool.importlinter] contracts in pyproject.toml."""

    def __init__(self, auditor: DependencyAuditorPort) -> None:
        """Initialize handler with DependencyAuditorPort adapter.

        Args:
            auditor: DependencyAuditorPort instance.
        """
        self._auditor = auditor

    def handle(self, command: GenerateImportLinterConfigCommand) -> bool:
        """Generate contracts across targeted or all packages.

        Args:
            command: GenerateImportLinterConfigCommand instance.

        Returns:
            True if any configuration was updated, False otherwise.
        """
        if command.packages:
            targets = list(command.packages)
        else:
            targets = get_package_directories(command.repo_root)

        modified = False
        for pkg in targets:
            if self._auditor.generate_import_linter_config(pkg):
                modified = True
        return modified


class RunUnifiedDepsAuditHandler:
    """Handler coordinating unified dependency health checks across workspace."""

    def __init__(self, auditor: DependencyAuditorPort) -> None:
        """Initialize handler with DependencyAuditorPort adapter.

        Args:
            auditor: DependencyAuditorPort instance.
        """
        self._auditor = auditor

    def handle(
        self, command: RunUnifiedDepsAuditCommand
    ) -> UnifiedDependencyAuditReport:
        """Execute unified dependency, extras, and architecture checks.

        Args:
            command: RunUnifiedDepsAuditCommand instance.

        Returns:
            UnifiedDependencyAuditReport domain model.
        """
        items: list[DependencyAuditItem] = []
        errors: list[str] = []

        # 1. Tool availability
        if command.check_tools:
            tool_errors: list[str] = []
            for import_name, desc, cli_cmd in _EXPECTED_TOOLS:
                ok, err = self._auditor.check_tool_availability(import_name, cli_cmd)
                if not ok:
                    tool_errors.append(
                        f"Tools Environment: Missing dependency for {desc} -> {err}"
                    )
            items.append(
                DependencyAuditItem(
                    check_name="Tool Environment Readiness",
                    passed=(len(tool_errors) == 0),
                    details="All required developer tools are installed"
                    if not tool_errors
                    else "Missing tools",
                )
            )
            errors.extend(tool_errors)

        # 2. Extras parity
        if command.check_extras:
            extras_res = self._auditor.audit_extras_parity(command.repo_root)
            items.append(
                DependencyAuditItem(
                    check_name=f"Packaging Extras Parity ({extras_res.total_packages_checked} packages)",
                    passed=extras_res.is_healthy,
                    details=f"{len(extras_res.violations)} missing extra(s)"
                    if not extras_res.is_healthy
                    else "100% forwarded",
                )
            )
            for v in extras_res.violations:
                errors.append(
                    f"Extras Parity: {v.subpackage}[{v.extra_name}] not properly forwarded in umbrella package."
                )

        # 3. Deptry source imports
        if command.check_deptry:
            deptry_errors: list[str] = []
            for pkg_dir in get_package_directories(command.repo_root):
                res = self._auditor.run_deptry(pkg_dir)
                if not res.passed:
                    deptry_errors.append(f"Deptry [{pkg_dir.name}]: {res.error_output}")
            items.append(
                DependencyAuditItem(
                    check_name="Deptry Source Import Audits",
                    passed=(len(deptry_errors) == 0),
                    details="All imports properly declared in pyproject.toml"
                    if not deptry_errors
                    else "Undeclared imports",
                )
            )
            errors.extend(deptry_errors)

        # 4. Diagrams
        diagram_generated = False
        if command.generate_diagrams:
            try:
                self._auditor.generate_architecture_diagrams(command.repo_root)
                diagram_generated = True
            except Exception as e:
                errors.append(f"Diagram Generation Error: {e}")

        is_healthy = len(errors) == 0
        return UnifiedDependencyAuditReport(
            items=tuple(items),
            errors=tuple(errors),
            is_healthy=is_healthy,
            diagram_generated=diagram_generated,
        )
