"""Domain models and commands for dependency, optional extras, and architecture boundary auditing.

Notes/Architectural Intent:
    Defines immutable domain entities and commands for validating packaging extras
    forwarding contracts, import boundaries (import-linter), code-level imports (deptry),
    and unified workspace dependency health.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from hexastack_core.domain.command import Command
from hexastack_tools.utils.extras_parity import ExtraParityViolation

__all__ = [
    "AuditExtrasParityCommand",
    "DependencyAuditItem",
    "DeptryAuditReport",
    "DeptryPackageResult",
    "ExtraParityViolation",
    "ExtrasAuditResult",
    "GenerateImportLinterConfigCommand",
    "ImportLinterPackageResult",
    "ImportLinterReport",
    "RunDeptryAuditCommand",
    "RunImportLinterCommand",
    "RunUnifiedDepsAuditCommand",
    "UnifiedDependencyAuditReport",
]


@dataclass(frozen=True)
class ExtrasAuditResult:
    """Aggregated outcome of an optional extras parity audit."""

    violations: tuple[ExtraParityViolation, ...]
    total_packages_checked: int

    @property
    def is_healthy(self) -> bool:
        """Return True if no parity violations were detected."""
        return len(self.violations) == 0


@dataclass(frozen=True)
class DeptryPackageResult:
    """Outcome of running deptry dependency audit on a single package."""

    package_name: str
    passed: bool
    error_output: str = ""


@dataclass(frozen=True)
class DeptryAuditReport:
    """Aggregated outcome of workspace-wide deptry auditing."""

    results: tuple[DeptryPackageResult, ...]
    exit_code: int


@dataclass(frozen=True)
class ImportLinterPackageResult:
    """Outcome of evaluating hexagonal architecture layer contracts on a package."""

    package_name: str
    passed: bool
    error_output: str = ""


@dataclass(frozen=True)
class ImportLinterReport:
    """Aggregated outcome of evaluating import-linter across workspace packages."""

    results: tuple[ImportLinterPackageResult, ...]
    exit_code: int


@dataclass(frozen=True)
class DependencyAuditItem:
    """A single diagnostic line item in the unified dependency audit report."""

    check_name: str
    passed: bool
    details: str = ""


@dataclass(frozen=True)
class UnifiedDependencyAuditReport:
    """Comprehensive health report spanning deptry, extras parity, and tool availability."""

    items: tuple[DependencyAuditItem, ...]
    errors: tuple[str, ...]
    is_healthy: bool
    diagram_generated: bool = False


# CQRS Commands


class AuditExtrasParityCommand(Command):
    """Command requesting validation of subpackage optional extras forwarding."""

    repo_root: Path
    generate_diagram: bool = False


class RunDeptryAuditCommand(Command):
    """Command requesting workspace-wide or targeted deptry source import audits."""

    repo_root: Path


class RunImportLinterCommand(Command):
    """Command requesting hexagonal architecture contract verification with import-linter."""

    repo_root: Path
    packages: tuple[Path, ...] = ()
    all_packages: bool = False


class GenerateImportLinterConfigCommand(Command):
    """Command requesting generation of [tool.importlinter] contracts in pyproject.toml."""

    repo_root: Path
    packages: tuple[Path, ...] = ()


class RunUnifiedDepsAuditCommand(Command):
    """Command requesting unified execution across deptry, extras parity, and architecture graphs."""

    repo_root: Path
    check_deptry: bool = True
    check_extras: bool = True
    check_tools: bool = True
    generate_diagrams: bool = False
