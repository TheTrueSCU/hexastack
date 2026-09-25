"""Domain models for hexastack-qual.

Notes/Architectural Intent:
    Pure Pydantic models encapsulating quality scorecards, complexity scores,
    parity findings, surviving mutant reports, and PR diagnostic summaries.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class ComplexityMetric(BaseModel):
    """Cognitive complexity measurement for a Python function or method.

    Notes/Architectural Intent:
        Captures cognitive complexity metrics according to complexipy standards
        to identify refactoring targets.
    """

    model_config = ConfigDict(frozen=True)

    function_name: str = Field(description="Name of the function or method.")
    file_path: str = Field(description="Relative path to the source file.")
    line_number: int = Field(description="Starting line number in source file.")
    complexity: int = Field(description="Measured cognitive complexity score.")
    is_violation: bool = Field(
        default=False,
        description="Whether complexity exceeds the threshold (default > 25).",
    )


class ParityFinding(BaseModel):
    """Symmetry record between a source module and its test file.

    Notes/Architectural Intent:
        Represents 1:1 test symmetry status between src/<pkg>/... and
        tests/unit/...
    """

    model_config = ConfigDict(frozen=True)

    source_file: str = Field(description="Relative path to the source file.")
    expected_test_file: str = Field(description="Expected matching unit test path.")
    exists: bool = Field(description="Whether the expected test file exists.")


class StatementFinding(BaseModel):
    """Integrity finding for __all__ export lists.

    Notes/Architectural Intent:
        Verifies casefold ordering and deduplication of public symbols in
        __all__.
    """

    model_config = ConfigDict(frozen=True)

    file_path: str = Field(description="Path to the python file checked.")
    is_sorted: bool = Field(description="Whether __all__ is alphabetically sorted.")
    is_deduplicated: bool = Field(description="Whether __all__ has no duplicates.")
    details: str = Field(default="", description="Diagnostic details or diff.")


class MutantFinding(BaseModel):
    """Inspection details for a single code mutant.

    Notes/Architectural Intent:
        Represents mutmut surviving mutant records classified into actionable,
        equivalent, or ignorable categories.
    """

    model_config = ConfigDict(frozen=True)

    mutant_id: str = Field(description="Unique mutant identifier or index.")
    file_path: str = Field(description="Source file path where mutation occurred.")
    line_number: int = Field(description="Line number of mutation.")
    operator: str = Field(default="", description="Mutation operator applied.")
    status: Literal["killed", "survived", "timeout", "skipped"] = Field(
        description="Outcome status of mutant execution."
    )
    triage_category: Literal["critical", "equivalent", "ignorable", "unclassified"] = (
        Field(
            default="unclassified",
            description="Triage severity classification.",
        )
    )
    covering_tests: list[str] = Field(
        default_factory=list,
        description="Test functions executing the mutated line.",
    )


class MutantReport(BaseModel):
    """Summary report of mutation testing execution.

    Notes/Architectural Intent:
        Aggregates mutation coverage metrics and counts of surviving mutants.
    """

    model_config = ConfigDict(frozen=True)

    package_name: str = Field(description="Target package name.")
    total_mutants: int = Field(default=0, description="Total mutants evaluated.")
    killed_mutants: int = Field(default=0, description="Count of killed mutants.")
    survived_mutants: int = Field(default=0, description="Count of surviving mutants.")
    mutation_score: float = Field(
        default=0.0,
        description="Percentage of killed mutants.",
    )
    actionable_survivors: list[MutantFinding] = Field(
        default_factory=list,
        description="List of critical actionable surviving mutants.",
    )


class QualityCheckResult(BaseModel):
    """Result of an individual quality check.

    Notes/Architectural Intent:
        Represents a single step outcome (e.g. Ruff, Ty, Complexity) in a sanity
        run.
    """

    model_config = ConfigDict(frozen=True)

    check_name: str = Field(description="Identifier for the check.")
    target: str = Field(description="Target package or component.")
    status: Literal["pass", "fail", "skip"] = Field(description="Outcome status.")
    duration_seconds: float = Field(
        default=0.0,
        description="Execution duration in seconds.",
    )
    details: str = Field(default="", description="Descriptive status message.")


class QualityScorecard(BaseModel):
    """Unified quality health scorecard for a package or workspace.

    Notes/Architectural Intent:
        The primary domain aggregate summarizing linting, type safety,
        complexity, test symmetry, and mutant survival across components.
    """

    model_config = ConfigDict(frozen=True)

    target: str = Field(description="Package name or 'workspace'.")
    is_healthy: bool = Field(description="Overall health status boolean.")
    checks: list[QualityCheckResult] = Field(
        default_factory=list,
        description="List of executed sanity checks.",
    )
    complexity_violations: list[ComplexityMetric] = Field(
        default_factory=list,
        description="List of functions exceeding complexity limits.",
    )
    parity_findings: list[ParityFinding] = Field(
        default_factory=list,
        description="List of test parity discrepancies.",
    )
    statement_findings: list[StatementFinding] = Field(
        default_factory=list,
        description="List of invalid __all__ statements.",
    )
    mutant_report: MutantReport | None = Field(
        default=None,
        description="Optional mutation testing summary.",
    )


class PrHealthSummary(BaseModel):
    """Diagnostic health summary for a GitHub Pull Request.

    Notes/Architectural Intent:
        Encapsulates CI check results, CodeQL security alerts, and review thread
        state.
    """

    model_config = ConfigDict(frozen=True)

    pr_number: int = Field(description="GitHub pull request number.")
    title: str = Field(description="Pull request title.")
    state: str = Field(description="PR state: open, closed, merged.")
    ci_status: Literal["pending", "success", "failure"] = Field(
        description="Aggregated CI check status."
    )
    total_checks: int = Field(default=0, description="Total CI check runs.")
    failed_checks: list[str] = Field(
        default_factory=list,
        description="Names of failing check runs.",
    )
    codeql_alerts_count: int = Field(
        default=0,
        description="Number of active CodeQL alerts.",
    )
    unresolved_threads_count: int = Field(
        default=0,
        description="Number of unresolved review comment threads.",
    )


__all__ = [
    "ComplexityMetric",
    "MutantFinding",
    "MutantReport",
    "ParityFinding",
    "PrHealthSummary",
    "QualityCheckResult",
    "QualityScorecard",
    "StatementFinding",
]
