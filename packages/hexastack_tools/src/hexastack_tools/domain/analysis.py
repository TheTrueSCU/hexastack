"""Domain models and CQRS commands for security scanning, fuzzing, and analysis.

Notes/Architectural Intent:
    Encapsulates command requests and output reports for CodeQL SAST scanning,
    Atheris/OWASP security fuzzing, and inline-snapshot updates without external
    subprocess or presentation dependencies.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from hexastack_core.domain.command import Command


@dataclass(frozen=True)
class CodeQlScanReport:
    """Summary report of local CodeQL database creation and query analysis.

    Attributes:
        sarif_path: Path to generated SARIF analysis output file if successful.
        findings_count: Total security or code quality alerts detected.
        critical_count: Number of high or critical severity alerts.
        error_message: Optional error message if database creation or query failed.
        is_successful: True if analysis completed cleanly without fatal errors.

    Notes/Architectural Intent:
        Represents CodeQL execution outcomes cleanly separated from console rendering.
    """

    sarif_path: Path | None = None
    findings_count: int = 0
    critical_count: int = 0
    error_message: str | None = None
    is_successful: bool = True


class ScanCodeQlCommand(Command):
    """CQRS Command to execute local CodeQL database creation and query suite.

    Attributes:
        query_suite: CodeQL query pack suite name (default: codeql/python-queries).
        output_sarif: Optional explicit target path for generated SARIF file.
        threads: Number of worker threads (0 for auto-detection).

    Notes/Architectural Intent:
        Dispatches CodeQL analysis through the governance bus.
    """

    query_suite: str = "codeql/python-queries"
    output_sarif: Path | None = None
    threads: int = 0


@dataclass(frozen=True)
class FuzzTargetResult:
    """Outcome metrics for a single fuzzing harness target.

    Attributes:
        target: Target name (e.g. 'sanitizer', 'proto', 'owasp').
        engine: Fuzzing engine used ('atheris', 'hypothesis', 'standalone').
        runs: Number of iterations executed.
        duration_seconds: Elapsed duration in seconds.
        crashes: Number of fatal crashes or uncaught exceptions detected.
        redos_violations: Algorithmic complexity / ReDoS threshold violations.
        passed: True if zero crashes and zero security violations detected.

    Notes/Architectural Intent:
        Encapsulates individual target metrics for multi-format presenters.
    """

    target: str
    engine: str
    runs: int
    duration_seconds: float
    crashes: int
    redos_violations: int
    passed: bool


@dataclass(frozen=True)
class FuzzRunReport:
    """Summary report of coverage-guided and security fuzz harness execution.

    Attributes:
        results: Tuple of individual target run results.
        all_passed: True if all targeted fuzz harnesses passed cleanly.

    Notes/Architectural Intent:
        Aggregates security fuzzing metrics across Atheris and OWASP targets.
    """

    results: tuple[FuzzTargetResult, ...] = ()
    all_passed: bool = True


class FuzzRunCommand(Command):
    """CQRS Command to execute fuzzing test harnesses.

    Attributes:
        target: Selected fuzzing target ('all', 'sanitizer', 'proto', 'owasp').
        runs: Number of iterations to execute per target.
        engine: Fuzzing engine mode ('auto', 'atheris', 'standalone').

    Notes/Architectural Intent:
        Decouples CLI options from harness execution and dynamic import logic.
    """

    target: str = "all"
    runs: int = 1000
    engine: str = "auto"


@dataclass(frozen=True)
class InlineSnapshotsReport:
    """Summary report of inline-snapshot update or review execution.

    Attributes:
        targets_updated: List of package or test paths processed.
        exit_code: Exit status code from pytest snapshot runner.

    Notes/Architectural Intent:
        Captures outcome of single-process inline-snapshot synchronization.
    """

    targets_updated: tuple[str, ...] = ()
    exit_code: int = 0


class UpdateInlineSnapshotsCommand(Command):
    """CQRS Command to update or review inline-snapshots across test suites.

    Attributes:
        mode: Snapshot execution mode ('create', 'fix', 'review').
        targets: Specific file or directory paths to target.

    Notes/Architectural Intent:
        Standardizes inline-snapshot invocation as a domain command.
    """

    mode: str = "fix"
    targets: tuple[Path, ...] = ()


__all__ = [
    "CodeQlScanReport",
    "FuzzRunCommand",
    "FuzzRunReport",
    "FuzzTargetResult",
    "InlineSnapshotsReport",
    "ScanCodeQlCommand",
    "UpdateInlineSnapshotsCommand",
]
