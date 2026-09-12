"""Domain models and CQRS commands for repository governance and sanity verification.

Notes/Architectural Intent:
    Pure domain models defining verification commands, results, and targets.
    Maintains zero external framework dependencies beyond hexastack_core primitives.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path

from hexastack_core.domain.command import Command

__all__ = [
    "AuditComplexityCommand",
    "CheckAllStatementsCommand",
    "CheckResult",
    "CheckStatus",
    "CheckTestParityCommand",
    "RunLinterCommand",
    "RunPytestCommand",
    "RunSanityCheckCommand",
    "RunTypecheckCommand",
    "SanityCheckReport",
    "SanityTarget",
]


class CheckStatus(StrEnum):
    """Execution status of a single governance check."""

    PASS = "PASS"  # noqa: S105
    FAIL = "FAIL"
    SKIP = "SKIP"


@dataclass(frozen=True)
class SanityTarget:
    """Target component scoped for governance checks."""

    name: str
    kind: str  # "package", "example", "file"
    path: Path
    src_paths: tuple[Path, ...]
    test_paths: tuple[Path, ...]


@dataclass(frozen=True)
class CheckResult:
    """Outcome and diagnostics for a single verification step."""

    check_name: str
    target_name: str
    status: CheckStatus
    duration: float
    details: str = ""
    error_output: str = ""


@dataclass(frozen=True)
class SanityCheckReport:
    """Aggregated report across all executed sanity checks."""

    results: tuple[CheckResult, ...]
    total_duration: float
    exit_code: int


class RunLinterCommand(Command):
    """Command requesting linting and code formatting check."""

    paths: tuple[Path, ...]
    target_name: str
    fix: bool = False


class RunTypecheckCommand(Command):
    """Command requesting static type checking."""

    paths: tuple[Path, ...]
    target_name: str


class AuditComplexityCommand(Command):
    """Command requesting cognitive complexity audit."""

    paths: tuple[Path, ...]
    target_name: str
    max_complexity: int = 25


class CheckAllStatementsCommand(Command):
    """Command requesting __all__ export integrity verification."""

    paths: tuple[Path, ...]
    target_name: str
    fix: bool = False


class CheckTestParityCommand(Command):
    """Command requesting 1:1 unit test symmetry check."""

    target: SanityTarget
    repo_root: Path


class RunPytestCommand(Command):
    """Command requesting test suite execution."""

    target: SanityTarget
    repo_root: Path
    skip: bool = False


class RunSanityCheckCommand(Command):
    """Composite command orchestrating full sanity check battery across targets."""

    targets: tuple[SanityTarget, ...]
    repo_root: Path
    fix: bool = False
    skip_tests: bool = False
    max_complexity: int = 25
