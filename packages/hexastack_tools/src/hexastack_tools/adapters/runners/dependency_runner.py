"""Concrete DependencyAuditorPort adapter executing deptry, import-linter, and extras audits.

Notes/Architectural Intent:
    Decouples system subprocess invocations and filesystem pyproject parsing
    from domain logic and command handlers.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

from hexastack_tools.domain.dependencies import (
    DeptryPackageResult,
    ExtrasAuditResult,
    ImportLinterPackageResult,
)
from hexastack_tools.ports.dependencies import DependencyAuditorPort
from hexastack_tools.utils.extras_parity import (
    audit_extras_parity as check_extras,
)
from hexastack_tools.utils.extras_parity import (
    generate_extras_mermaid_diagram as make_mermaid,
)
from hexastack_tools.utils.import_linter import update_pyproject_toml
from hexastack_tools.utils.pydeps import generate_all_diagrams
from hexastack_tools.utils.workspace import (
    check_tool_availability as check_tool_avail,
)
from hexastack_tools.utils.workspace import (
    get_package_directories,
)

__all__ = [
    "SubprocessDependencyAuditorAdapter",
]


class SubprocessDependencyAuditorAdapter(DependencyAuditorPort):
    """Subprocess and filesystem execution adapter for dependency and boundary audits."""

    def audit_extras_parity(self, repo_root: Path) -> ExtrasAuditResult:
        """Audit subpackage optional dependencies against umbrella packaging forwarding.

        Args:
            repo_root: Root path of repository workspace.

        Returns:
            ExtrasAuditResult domain model.
        """
        violations = check_extras(repo_root)
        total_packages = len(get_package_directories(repo_root))
        return ExtrasAuditResult(
            violations=tuple(violations),
            total_packages_checked=total_packages,
        )

    def generate_extras_diagram(self, repo_root: Path) -> str:
        """Generate Mermaid dependency diagram for optional extras.

        Args:
            repo_root: Root path of repository workspace.

        Returns:
            Mermaid diagram markdown string.
        """
        return make_mermaid(repo_root)

    def run_deptry(self, pkg_dir: Path) -> DeptryPackageResult:
        """Execute deptry import check for a package directory.

        Args:
            pkg_dir: Target package directory path.

        Returns:
            DeptryPackageResult domain model.
        """
        pyproject = pkg_dir / "pyproject.toml"
        if not pyproject.is_file():
            return DeptryPackageResult(package_name=pkg_dir.name, passed=True)

        cmd = [
            "deptry",
            str(pkg_dir),
            "--config",
            str(pyproject),
            "--known-first-party",
            pkg_dir.name,
            "--ignore",
            "DEP002,DEP003,DEP004",
        ]
        res = subprocess.run(cmd, capture_output=True, text=True)
        if res.returncode != 0:
            err = (res.stdout.strip() + "\n" + res.stderr.strip()).strip()
            return DeptryPackageResult(
                package_name=pkg_dir.name, passed=False, error_output=err
            )
        return DeptryPackageResult(package_name=pkg_dir.name, passed=True)

    def run_import_linter(self, pkg_dir: Path) -> ImportLinterPackageResult:
        """Run lint-imports contract evaluation on a package.

        Args:
            pkg_dir: Target package directory path.

        Returns:
            ImportLinterPackageResult domain model.
        """
        pyproject = pkg_dir / "pyproject.toml"
        if not pyproject.is_file():
            return ImportLinterPackageResult(package_name=pkg_dir.name, passed=True)

        res = subprocess.run(
            ["lint-imports", "--config", str(pyproject)],
            capture_output=True,
            text=True,
        )
        if res.returncode != 0:
            err = (res.stdout.strip() + "\n" + res.stderr.strip()).strip()
            return ImportLinterPackageResult(
                package_name=pkg_dir.name, passed=False, error_output=err
            )
        return ImportLinterPackageResult(package_name=pkg_dir.name, passed=True)

    def generate_import_linter_config(self, pkg_dir: Path) -> bool:
        """Generate or update [tool.importlinter] contracts in pyproject.toml.

        Args:
            pkg_dir: Target package directory path.

        Returns:
            True if config generated or updated, False otherwise.
        """
        return update_pyproject_toml(pkg_dir)

    def generate_architecture_diagrams(self, repo_root: Path) -> None:
        """Regenerate Pydeps SVG import graphs across packages.

        Args:
            repo_root: Root path of repository workspace.
        """
        generate_all_diagrams(repo_root)

    def check_tool_availability(
        self,
        import_name: str,
        cli_command: str | None = None,
    ) -> tuple[bool, str]:
        """Verify availability of an external CLI tool in the environment.

        Args:
            import_name: Python module or package import name.
            cli_command: Optional CLI binary command name.

        Returns:
            Tuple of (is_available, error_message).
        """
        return check_tool_avail(import_name, cli_command)
