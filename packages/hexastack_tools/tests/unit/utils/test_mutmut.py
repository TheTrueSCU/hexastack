"""Unit tests for mutant classification heuristics.

Notes/Architectural Intent:
    Verifies that classify_mutant_line accurately categorizes lines as CRITICAL,
    EQUIVALENT, or IGNORABLE based on regex heuristics and filepath context.
"""

from __future__ import annotations

from hexastack_tools.utils.mutmut import classify_mutant_line


def test_classify_ignorable_logging() -> None:
    """Verify logging calls are classified as IGNORABLE."""
    cat, rationale = classify_mutant_line(
        "logger.info('Processing item')", "src/service.py"
    )
    assert cat == "IGNORABLE"
    assert "Log" in rationale


def test_classify_ignorable_test_harness() -> None:
    """Verify files inside testing harnesses are classified as IGNORABLE."""
    cat, rationale = classify_mutant_line(
        "x = 42", "packages/core/src/testing/harness.py"
    )
    assert cat == "IGNORABLE"
    assert "Test harness" in rationale


def test_classify_equivalent_none_default() -> None:
    """Verify default None parameters are classified as EQUIVALENT."""
    cat, rationale = classify_mutant_line(
        "def foo(bar: str | None = None):", "src/service.py"
    )
    assert cat == "EQUIVALENT"


def test_classify_critical_control_flow() -> None:
    """Verify branching and assertion statements are classified as CRITICAL."""
    cat, rationale = classify_mutant_line("if user.is_active:", "src/service.py")
    assert cat == "CRITICAL"
    assert "Control flow" in rationale


def test_classify_critical_security() -> None:
    """Verify auth/token logic is classified as CRITICAL."""
    cat, rationale = classify_mutant_line(
        "validated_token = decode(token)", "src/service.py"
    )
    assert cat == "CRITICAL"
    assert "security" in rationale.lower()
