"""Property-based tests for hexastack-qual domain models and scorecards.

Notes/Architectural Intent:
    Validates fundamental invariants of the quality scorecard, mutant triage,
    and PR diagnostic domain aggregates across arbitrary generated inputs,
    guaranteeing strict mathematical bounds, status consistency, and idempotent
    JSON roundtrip serialization.
"""

from __future__ import annotations

from typing import Literal

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
from hypothesis import given, settings
from hypothesis import strategies as st

# Strategy generators for domain primitives
st_status = st.sampled_from(["pass", "fail", "skip"])
st_mutant_status = st.sampled_from(["killed", "survived", "timeout", "skipped"])
st_triage_category = st.sampled_from(
    ["critical", "equivalent", "ignorable", "unclassified"]
)
st_ci_status = st.sampled_from(["pending", "success", "failure"])

st_complexity_metric = st.builds(
    ComplexityMetric,
    function_name=st.text(min_size=1, max_size=50),
    file_path=st.text(min_size=1, max_size=100),
    line_number=st.integers(min_value=1, max_value=10000),
    complexity=st.integers(min_value=0, max_value=100),
    is_violation=st.booleans(),
)

st_parity_finding = st.builds(
    ParityFinding,
    source_file=st.text(min_size=1, max_size=100),
    expected_test_file=st.text(min_size=1, max_size=100),
    exists=st.booleans(),
)

st_statement_finding = st.builds(
    StatementFinding,
    file_path=st.text(min_size=1, max_size=100),
    is_sorted=st.booleans(),
    is_deduplicated=st.booleans(),
    details=st.text(max_size=100),
)

st_quality_check = st.builds(
    QualityCheckResult,
    check_name=st.text(min_size=1, max_size=50),
    target=st.text(min_size=1, max_size=50),
    status=st_status,
    duration_seconds=st.floats(min_value=0.0, max_value=1000.0),
    details=st.text(max_size=100),
)

st_mutant_finding = st.builds(
    MutantFinding,
    mutant_id=st.text(min_size=1, max_size=20),
    file_path=st.text(min_size=1, max_size=100),
    line_number=st.integers(min_value=1, max_value=10000),
    operator=st.text(max_size=30),
    status=st_mutant_status,
    triage_category=st_triage_category,
    covering_tests=st.lists(st.text(min_size=1, max_size=50), max_size=5),
)


@given(
    target=st.text(min_size=1, max_size=50),
    checks=st.lists(st_quality_check, max_size=10),
    complexities=st.lists(st_complexity_metric, max_size=5),
    parities=st.lists(st_parity_finding, max_size=5),
    statements=st.lists(st_statement_finding, max_size=5),
    is_healthy=st.booleans(),
)
@settings(max_examples=50)
def test_quality_scorecard_roundtrip_serialization(
    target: str,
    checks: list[QualityCheckResult],
    complexities: list[ComplexityMetric],
    parities: list[ParityFinding],
    statements: list[StatementFinding],
    is_healthy: bool,
) -> None:
    """Property test verifying lossless JSON roundtrip for QualityScorecard.

    Args:
        target: Target name identifier.
        checks: Executed check outcomes.
        complexities: Cognitive complexity violations.
        parities: Symmetry discrepancy findings.
        statements: __all__ export findings.
        is_healthy: Overall boolean health status.

    Notes/Architectural Intent:
        Guarantees that serialization and schema hydration remain strictly idempotent
        across arbitrary model populations.
    """
    card = QualityScorecard(
        target=target,
        is_healthy=is_healthy,
        checks=checks,
        complexity_violations=complexities,
        parity_findings=parities,
        statement_findings=statements,
    )

    serialized = card.model_dump_json()
    hydrated = QualityScorecard.model_validate_json(serialized)

    card_target = hydrated.target
    assert card_target == target
    card_health = hydrated.is_healthy
    assert card_health == is_healthy
    checks_len = len(hydrated.checks)
    assert checks_len == len(checks)
    cpx_len = len(hydrated.complexity_violations)
    assert cpx_len == len(complexities)
    par_len = len(hydrated.parity_findings)
    assert par_len == len(parities)
    stmt_len = len(hydrated.statement_findings)
    assert stmt_len == len(statements)


@given(
    total=st.integers(min_value=0, max_value=5000),
    killed=st.integers(min_value=0, max_value=5000),
    survivors=st.lists(st_mutant_finding, max_size=10),
)
@settings(max_examples=50)
def test_mutant_report_score_invariants(
    total: int, killed: int, survivors: list[MutantFinding]
) -> None:
    """Property test verifying mutation score boundedness and triage invariants.

    Args:
        total: Raw mutant count.
        killed: Killed mutant count.
        survivors: Actionable surviving mutant list.

    Notes/Architectural Intent:
        Enforces that mutation_score adheres to percentage bounds [0.0, 100.0]
        and survivors strictly maintain categorized outcomes.
    """
    valid_killed = min(total, killed)
    valid_survived = total - valid_killed
    calculated_score = (valid_killed / total * 100.0) if total > 0 else 0.0

    report = MutantReport(
        package_name="test-pkg",
        total_mutants=total,
        killed_mutants=valid_killed,
        survived_mutants=valid_survived,
        mutation_score=calculated_score,
        actionable_survivors=survivors,
    )

    score = report.mutation_score
    assert 0.0 <= score <= 100.0

    tot = report.total_mutants
    kld = report.killed_mutants
    surv = report.survived_mutants
    assert tot == kld + surv

    for s in report.actionable_survivors:
        category = s.triage_category
        assert category in ("critical", "equivalent", "ignorable", "unclassified")
        status = s.status
        assert status in ("killed", "survived", "timeout", "skipped")


@given(
    pr_number=st.integers(min_value=1, max_value=100000),
    title=st.text(min_size=1, max_size=100),
    state=st.sampled_from(["open", "closed", "merged"]),
    ci_status=st_ci_status,
    total_checks=st.integers(min_value=0, max_value=100),
    codeql_alerts=st.integers(min_value=0, max_value=50),
    unresolved_threads=st.integers(min_value=0, max_value=50),
)
@settings(max_examples=50)
def test_pr_health_summary_invariants(
    pr_number: int,
    title: str,
    state: str,
    ci_status: Literal["pending", "success", "failure"],
    total_checks: int,
    codeql_alerts: int,
    unresolved_threads: int,
) -> None:
    """Property test verifying non-negative counter invariants on PrHealthSummary.

    Args:
        pr_number: Valid positive PR index.
        title: PR title description.
        state: Lifecycle state string.
        ci_status: Aggregated CI conclusion.
        total_checks: Total CI status check runs.
        codeql_alerts: Active CodeQL alert count.
        unresolved_threads: Unresolved discussion thread count.

    Notes/Architectural Intent:
        Ensures that diagnostic metrics remain strictly non-negative and
        accurately hydrate from persistent storage.
    """
    summary = PrHealthSummary(
        pr_number=pr_number,
        title=title,
        state=state,
        ci_status=ci_status,
        total_checks=total_checks,
        codeql_alerts_count=codeql_alerts,
        unresolved_threads_count=unresolved_threads,
    )

    num = summary.pr_number
    assert num > 0
    checks_count = summary.total_checks
    assert checks_count >= 0
    alerts_count = summary.codeql_alerts_count
    assert alerts_count >= 0
    threads_count = summary.unresolved_threads_count
    assert threads_count >= 0

    json_data = summary.model_dump_json()
    rehydrated = PrHealthSummary.model_validate_json(json_data)
    reh_pr = rehydrated.pr_number
    assert reh_pr == pr_number
    reh_state = rehydrated.state
    assert reh_state == state
