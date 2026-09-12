"""Port contracts for dependency auditing and dependency presentation.

Notes/Architectural Intent:
    Defines abstract interfaces separating packaging extras evaluation,
    import boundary checks (import-linter), code import audits (deptry),
    and diagram generation from concrete execution runners and UI formatting.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path

from hexastack_tools.domain.dependencies import (
    DeptryAuditReport,
    DeptryPackageResult,
    ExtrasAuditResult,
    ImportLinterPackageResult,
    ImportLinterReport,
    UnifiedDependencyAuditReport,
)

__all__ = [
    "DependencyAuditorPort",
    "DependencyPresenterPort",
]


class DependencyAuditorPort(ABC):
    """Abstract port for executing dependency, extras, and architecture boundary audits."""

    @abstractmethod
    def audit_extras_parity(self, repo_root: Path) -> ExtrasAuditResult:
        """Audit subpackage optional dependencies against umbrella packaging forwarding.

        Args:
            repo_root: Root path of the repository workspace.

        Returns:
            ExtrasAuditResult with detected forwarding violations.
        """

    @abstractmethod
    def generate_extras_diagram(self, repo_root: Path) -> str:
        """Generate a Mermaid dependency graph of all umbrella and subpackage extras.

        Args:
            repo_root: Root path of the repository workspace.

        Returns:
            Mermaid diagram markdown string.
        """

    @abstractmethod
    def run_deptry(self, pkg_dir: Path) -> DeptryPackageResult:
        """Execute deptry import check for a single package directory.

        Args:
            pkg_dir: Target package directory path.

        Returns:
            DeptryPackageResult with execution status and diagnostics.
        """

    @abstractmethod
    def run_import_linter(self, pkg_dir: Path) -> ImportLinterPackageResult:
        """Run import-linter contract check for a single package.

        Args:
            pkg_dir: Target package directory path.

        Returns:
            ImportLinterPackageResult with contract status and diagnostics.
        """

    @abstractmethod
    def generate_import_linter_config(self, pkg_dir: Path) -> bool:
        """Generate or synchronize [tool.importlinter] contracts in pyproject.toml.

        Args:
            pkg_dir: Target package directory path.

        Returns:
            True if config was generated or updated, False otherwise.
        """

    @abstractmethod
    def generate_architecture_diagrams(self, repo_root: Path) -> None:
        """Regenerate Pydeps SVG import graphs and extras diagrams.

        Args:
            repo_root: Root path of the repository workspace.
        """

    @abstractmethod
    def check_tool_availability(
        self,
        import_name: str,
        cli_command: str | None = None,
    ) -> tuple[bool, str]:
        """Check if an external tool is installed and available in the environment.

        Args:
            import_name: Python module or package import name.
            cli_command: Optional CLI binary command name.

        Returns:
            Tuple of (is_available, failure_reason_or_empty).
        """


class DependencyPresenterPort(ABC):
    """Abstract port for presenting dependency and packaging reports across formats."""

    @abstractmethod
    def present_extras_parity(
        self,
        result: ExtrasAuditResult,
        diagram: str | None = None,
    ) -> int:
        """Render extras parity audit outcomes or Mermaid dependency diagram.

        Args:
            result: ExtrasAuditResult domain object.
            diagram: Optional generated Mermaid diagram string.

        Returns:
            Process exit code (0 for pass, 1 for failure).
        """

    @abstractmethod
    def present_deptry_audit(self, report: DeptryAuditReport) -> int:
        """Render workspace-wide deptry import audit results.

        Args:
            report: DeptryAuditReport domain object.

        Returns:
            Process exit code (0 for pass, 1 for failure).
        """

    @abstractmethod
    def present_import_linter(self, report: ImportLinterReport) -> int:
        """Render hexagonal architecture layer contract evaluations.

        Args:
            report: ImportLinterReport domain object.

        Returns:
            Process exit code (0 for pass, 1 for failure).
        """

    @abstractmethod
    def present_unified_deps_audit(
        self,
        report: UnifiedDependencyAuditReport,
    ) -> int:
        """Render unified dependency audit dashboard.

        Args:
            report: UnifiedDependencyAuditReport domain object.

        Returns:
            Process exit code (0 for pass, 1 for failure).
        """
