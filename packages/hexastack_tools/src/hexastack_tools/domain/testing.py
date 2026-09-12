"""Domain models and commands for mutation testing, test boundary audits, and test impact analysis.

Notes/Architectural Intent:
    Defines immutable domain structures for mutmut mutation inspection,
    coverage-guided boundary audits, test redundancy tracking, and Test Impact Analysis (TIA).
"""

from __future__ import annotations

import enum
from dataclasses import dataclass
from pathlib import Path

from hexastack_core.domain.command import Command

__all__ = [
    "AuditTestBoundariesCommand",
    "AuditTestRedundancyCommand",
    "BoundaryAuditItem",
    "BoundaryAuditReport",
    "ImpactedTestsReport",
    "InspectMutationCacheCommand",
    "MutantCategory",
    "MutantRecord",
    "MutationAuditReport",
    "MutationPackageSummary",
    "RedundancyAuditReport",
    "RedundantTestItem",
    "RunImpactedTestsCommand",
    "RunMutationTestsCommand",
]


class MutantCategory(enum.StrEnum):
    """Classification category for surviving mutants based on triage severity."""

    CRITICAL = "CRITICAL"
    EQUIVALENT = "EQUIVALENT"
    IGNORABLE = "IGNORABLE"


@dataclass(frozen=True)
class MutantRecord:
    """Detailed record of a surviving or timeout mutant."""

    id: str
    filename: str
    line_number: int
    line_content: str
    category: MutantCategory
    rationale: str
    covering_tests: tuple[str, ...] = ()


@dataclass(frozen=True)
class MutationPackageSummary:
    """Aggregated mutant triage counts for a specific package."""

    package_name: str
    total: int
    critical: int
    equivalent: int
    ignorable: int


@dataclass(frozen=True)
class MutationAuditReport:
    """Aggregated mutation testing summary and optional actionable mutants list."""

    summaries: tuple[MutationPackageSummary, ...]
    actionable_mutants: tuple[MutantRecord, ...] = ()

    @property
    def total_critical(self) -> int:
        """Total critical surviving mutants across all packages."""
        return sum(s.critical for s in self.summaries)


@dataclass(frozen=True)
class BoundaryAuditItem:
    """Represents an architectural boundary leak in test execution contexts."""

    test_context: str
    leaked_file: str


@dataclass(frozen=True)
class BoundaryAuditReport:
    """Result of auditing test execution contexts for layer boundary leaks."""

    leaks: tuple[BoundaryAuditItem, ...]

    @property
    def is_healthy(self) -> bool:
        """Return True if zero boundary leaks were detected."""
        return len(self.leaks) == 0


@dataclass(frozen=True)
class RedundantTestItem:
    """Represents a test that covers zero unique branch arcs."""

    test_context: str


@dataclass(frozen=True)
class RedundancyAuditReport:
    """Result of auditing coverage branch arcs for redundant tests."""

    redundant_tests: tuple[str, ...]


@dataclass(frozen=True)
class ImpactedTestsReport:
    """Result of correlating modified lines to coverage execution contexts."""

    changed_files: tuple[str, ...]
    impacted_tests: tuple[str, ...]
    dry_run: bool = False
    exit_code: int = 0


# CQRS Commands


class RunMutationTestsCommand(Command):
    """Command requesting execution of mutmut mutation testing."""

    package: str | None = None
    all_packages: bool = False
    reset_cache: bool = False


class InspectMutationCacheCommand(Command):
    """Command requesting inspection and triage of .mutmut-cache SQLite database."""

    cache_file: Path = Path(".mutmut-cache")
    package: str | None = None
    actionable_only: bool = False
    correlate_coverage: bool = False
    coverage_file: Path | None = None


class AuditTestBoundariesCommand(Command):
    """Command requesting layer boundary audit across test contexts in .coverage."""

    coverage_file: Path = Path(".coverage")


class AuditTestRedundancyCommand(Command):
    """Command requesting audit of redundant tests in .coverage branch arcs."""

    coverage_file: Path = Path(".coverage")


class RunImpactedTestsCommand(Command):
    """Command requesting Test Impact Analysis (TIA) and selective pytest execution."""

    repo_root: Path = Path()
    base_ref: str | None = None
    coverage_file: Path | None = None
    dry_run: bool = False
    pytest_args: tuple[str, ...] = ()
