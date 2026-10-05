"""Unit tests for hexastack-qual domain models.

Notes/Architectural Intent:
    Validates model instantiation, immutability, serialization, and default
    values across quality models.
"""

from __future__ import annotations

import pytest
from hexastack_qual.domain.models import (
    ComplexityMetric,
    MutantFinding,
    MutantReport,
    ParityFinding,
    PrHealthSummary,
    QualityCheckResult,
    QualityScorecard,
    StatementFinding,
)
from pydantic import ValidationError


def test_complexity_metric_model() -> None:
    """Ensure ComplexityMetric stores properties and immutability."""
    metric = ComplexityMetric(
        function_name="process_orders",
        file_path="src/orders/service.py",
        line_number=42,
        complexity=18,
        is_violation=False,
    )
    assert metric.function_name == "process_orders"
    assert metric.file_path == "src/orders/service.py"
    assert metric.line_number == 42
    assert metric.complexity == 18
    assert metric.is_violation is False

    attr_name = "complexity"
    with pytest.raises(ValidationError):
        setattr(metric, attr_name, 30)


def test_parity_finding_model() -> None:
    """Ensure ParityFinding records source to test symmetry."""
    finding = ParityFinding(
        source_file="src/auth/jwt.py",
        expected_test_file="tests/unit/auth/test_jwt.py",
        exists=True,
    )
    assert finding.source_file == "src/auth/jwt.py"
    assert finding.expected_test_file == "tests/unit/auth/test_jwt.py"
    assert finding.exists is True


def test_statement_finding_model() -> None:
    """Ensure StatementFinding captures __all__ validation results."""
    finding = StatementFinding(
        file_path="src/pkg/__init__.py",
        is_sorted=True,
        is_deduplicated=True,
        details="Clean",
    )
    assert finding.is_sorted is True
    assert finding.is_deduplicated is True
    assert finding.details == "Clean"


def test_mutant_finding_and_report_models() -> None:
    """Ensure MutantFinding and MutantReport properly aggregate."""
    finding = MutantFinding(
        mutant_id="142",
        file_path="src/cqrs/bus.py",
        line_number=88,
        operator="negate_condition",
        status="survived",
        triage_category="critical",
        covering_tests=["tests.unit.test_bus.test_dispatch"],
    )
    assert finding.mutant_id == "142"
    assert finding.status == "survived"
    assert finding.triage_category == "critical"
    assert len(finding.covering_tests) == 1

    report = MutantReport(
        package_name="cqrs",
        total_mutants=100,
        killed_mutants=92,
        survived_mutants=8,
        mutation_score=92.0,
        actionable_survivors=[finding],
    )
    assert report.package_name == "cqrs"
    assert report.total_mutants == 100
    assert report.killed_mutants == 92
    assert report.survived_mutants == 8
    assert report.mutation_score == 92.0
    assert len(report.actionable_survivors) == 1


def test_quality_scorecard_model() -> None:
    """Ensure QualityScorecard combines all sub-metrics cleanly."""
    check = QualityCheckResult(
        check_name="Ruff",
        target="core",
        status="pass",
        duration_seconds=0.12,
        details="Clean",
    )
    scorecard = QualityScorecard(
        target="core",
        is_healthy=True,
        checks=[check],
        complexity_violations=[],
        parity_findings=[],
        statement_findings=[],
        mutant_report=None,
    )
    assert scorecard.target == "core"
    assert scorecard.is_healthy is True
    assert len(scorecard.checks) == 1
    assert len(scorecard.complexity_violations) == 0
    assert scorecard.mutant_report is None


def test_pr_health_summary_model() -> None:
    """Ensure PrHealthSummary reflects GitHub pull request diagnostic state."""
    pr_summary = PrHealthSummary(
        pr_number=42,
        title="feat(qual): add adapter",
        state="open",
        ci_status="success",
        total_checks=5,
        failed_checks=[],
        codeql_alerts_count=0,
        unresolved_threads_count=1,
    )
    assert pr_summary.pr_number == 42
    assert pr_summary.title == "feat(qual): add adapter"
    assert pr_summary.ci_status == "success"
    assert pr_summary.codeql_alerts_count == 0
    assert pr_summary.unresolved_threads_count == 1
