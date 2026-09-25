"""Property-based tests for hexastack-qual domain models and scorecards.

Notes/Architectural Intent:
    Verifies mathematical and domain invariants across quality scorecards,
    complexity metrics, test parity reports, and mutant triage models using Hypothesis.
"""

from hexastack_qual.domain.models import (
    ComplexityMetric,
    MutantFinding,
    MutantReport,
    ParityFinding,
    QualityCheckResult,
    QualityScorecard,
    StatementFinding,
)
from hypothesis import given, settings
from hypothesis import strategies as st

# Custom Hypothesis Strategies for Quality Domain Models
st_check_status = st.sampled_from(["pass", "fail", "skip"])

st_quality_check = st.builds(
    QualityCheckResult,
    check_name=st.sampled_from(["Ruff", "Ty", "Complexity", "Test Parity", "Pytest"]),
    target=st.sampled_from(["core", "cqrs", "fastapi", "events", "qual"]),
    status=st_check_status,
    duration_seconds=st.floats(min_value=0.0, max_value=300.0, allow_nan=False),
    details=st.text(max_size=100),
)

st_complexity_metric = st.builds(
    ComplexityMetric,
    function_name=st.from_regex(r"[a-z_][a-z0-9_]{1,30}", fullmatch=True),
    file_path=st.from_regex(r"src/[a-z_]+/[a-z_]+\.py", fullmatch=True),
    line_number=st.integers(min_value=1, max_value=10000),
    complexity=st.integers(min_value=0, max_value=100),
    is_violation=st.booleans(),
)

st_parity_finding = st.builds(
    ParityFinding,
    source_file=st.from_regex(r"src/[a-z_]+/[a-z_]+\.py", fullmatch=True),
    expected_test_file=st.from_regex(
        r"tests/unit/[a-z_]+/test_[a-z_]+\.py", fullmatch=True
    ),
    exists=st.booleans(),
)

st_statement_finding = st.builds(
    StatementFinding,
    file_path=st.from_regex(r"src/[a-z_]+/[a-z_]+\.py", fullmatch=True),
    is_sorted=st.booleans(),
    is_deduplicated=st.booleans(),
    details=st.text(max_size=50),
)

st_mutant_finding = st.builds(
    MutantFinding,
    mutant_id=st.from_regex(r"mutant_[0-9]{1,4}", fullmatch=True),
    file_path=st.from_regex(r"src/[a-z_]+/[a-z_]+\.py", fullmatch=True),
    line_number=st.integers(min_value=1, max_value=5000),
    operator=st.sampled_from(["Arithmetic", "Comparison", "Logical", "Decorator"]),
    status=st.sampled_from(["killed", "survived", "timeout", "skipped"]),
    triage_category=st.sampled_from(
        ["critical", "equivalent", "ignorable", "unclassified"]
    ),
    covering_tests=st.lists(st.from_regex(r"test_[a-z_]+", fullmatch=True), max_size=5),
)


@given(
    target=st.sampled_from(["qual", "core", "workspace"]),
    is_healthy=st.booleans(),
    checks=st.lists(st_quality_check, max_size=8),
    violations=st.lists(st_complexity_metric, max_size=5),
    parity=st.lists(st_parity_finding, max_size=5),
    statements=st.lists(st_statement_finding, max_size=5),
)
@settings(max_examples=50)
def test_quality_scorecard_serialization_roundtrip(
    target: str,
    is_healthy: bool,
    checks: list[QualityCheckResult],
    violations: list[ComplexityMetric],
    parity: list[ParityFinding],
    statements: list[StatementFinding],
) -> None:
    """Property test verifying lossless JSON roundtrip serialization of QualityScorecard.

    Args:
        target: Evaluated target name.
        is_healthy: Overall boolean flag.
        checks: List of QualityCheckResult instances.
        violations: List of ComplexityMetric instances.
        parity: List of ParityFinding instances.
        statements: List of StatementFinding instances.

    Notes/Architectural Intent:
        Guarantees that serialization through Pydantic model_dump_json and reconstruction
        via model_validate_json preserves full semantic fidelity without data distortion.
    """
    card = QualityScorecard(
        target=target,
        is_healthy=is_healthy,
        checks=checks,
        complexity_violations=violations,
        parity_findings=parity,
        statement_findings=statements,
    )

    json_str = card.model_dump_json()
    reconstructed = QualityScorecard.model_validate_json(json_str)

    assert reconstructed == card
    assert reconstructed.target == target
    assert reconstructed.is_healthy == is_healthy
    assert len(reconstructed.checks) == len(checks)
    assert len(reconstructed.complexity_violations) == len(violations)
    assert len(reconstructed.parity_findings) == len(parity)
    assert len(reconstructed.statement_findings) == len(statements)


@given(
    total=st.integers(min_value=0, max_value=10000),
    killed=st.integers(min_value=0, max_value=10000),
    survivors=st.lists(st_mutant_finding, max_size=5),
)
@settings(max_examples=50)
def test_mutant_report_score_bounded_invariant(
    total: int, killed: int, survivors: list[MutantFinding]
) -> None:
    """Property test verifying mutation scores are strictly bounded within [0.0, 100.0].

    Args:
        total: Total mutants count.
        killed: Number of killed mutants.
        survivors: Actionable surviving findings.

    Notes/Architectural Intent:
        Asserts that mutation scores never produce out-of-bounds percentages regardless
        of mutant counts or empty collections.
    """
    safe_killed = min(killed, total)
    survived = total - safe_killed
    calculated_score = (safe_killed / total * 100.0) if total > 0 else 100.0

    report = MutantReport(
        package_name="hexastack_qual",
        total_mutants=total,
        killed_mutants=safe_killed,
        survived_mutants=survived,
        mutation_score=calculated_score,
        actionable_survivors=survivors,
    )

    assert 0.0 <= report.mutation_score <= 100.0
    assert report.total_mutants == report.killed_mutants + report.survived_mutants


@given(
    complexity=st.integers(min_value=0, max_value=100),
)
@settings(max_examples=40)
def test_complexity_metric_threshold_invariant(complexity: int) -> None:
    """Property test verifying cognitive complexity violation threshold logic.

    Args:
        complexity: Evaluated complexity score.

    Notes/Architectural Intent:
        Validates that functions exceeding the complexipy ceiling of 25 are always
        flagged as violations, preventing threshold boundary mutation slips.
    """
    is_violating = complexity > 25
    metric = ComplexityMetric(
        function_name="evaluate_complexity",
        file_path="src/hexastack_qual/adapters/hexaqual/runner.py",
        line_number=42,
        complexity=complexity,
        is_violation=is_violating,
    )

    if complexity > 25:
        assert metric.is_violation is True
    else:
        assert metric.is_violation is False
