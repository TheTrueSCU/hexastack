"""Unit tests for QualityAuditorPort interface.

Notes/Architectural Intent:
    Ensures QualityAuditorPort cannot be instantiated directly and that
    concrete subclasses correctly satisfy abstract method requirements.
"""

from __future__ import annotations

import inspect

import pytest
from hexastack_qual.domain.models import (
    ComplexityMetric,
    ParityFinding,
    QualityScorecard,
    StatementFinding,
)
from hexastack_qual.ports.auditor import QualityAuditorPort


class DummyAuditor(QualityAuditorPort):
    """Concrete dummy implementation for interface testing."""

    def audit_complexity(
        self,
        package: str | None = None,
        max_complexity: int = 25,
    ) -> list[ComplexityMetric]:
        return []

    def audit_parity(
        self,
        package: str | None = None,
    ) -> list[ParityFinding]:
        return []

    def audit_statements(
        self,
        package: str | None = None,
    ) -> list[StatementFinding]:
        return []

    def fix_statements(
        self,
        package: str | None = None,
    ) -> int:
        return 0

    def run_sanity(
        self,
        package: str | None = None,
        skip_tests: bool = True,
    ) -> QualityScorecard:
        return QualityScorecard(target="test", is_healthy=True)


def test_quality_auditor_port_cannot_instantiate_abstract() -> None:
    """Ensure abstract port cannot be instantiated directly."""
    with pytest.raises(TypeError):
        QualityAuditorPort()  # ty: ignore[call-non-callable]


def test_concrete_auditor_satisfies_contract() -> None:
    """Ensure concrete implementation works cleanly."""
    auditor = DummyAuditor()
    complexity = auditor.audit_complexity("core")
    parity = auditor.audit_parity("core")
    statements = auditor.audit_statements("core")
    fixed = auditor.fix_statements("core")
    sanity = auditor.run_sanity("core")

    assert complexity == []
    assert parity == []
    assert statements == []
    assert fixed == 0
    assert sanity.is_healthy is True


def test_quality_auditor_port_is_abstract() -> None:
    """Verify that QualityAuditorPort cannot be instantiated directly and is abstract."""
    is_abs = inspect.isabstract(QualityAuditorPort)
    assert is_abs is True
    with pytest.raises(TypeError, match="Can't instantiate abstract class"):
        QualityAuditorPort()  # ty: ignore[call-non-callable] # type: ignore[abstract]


def test_quality_auditor_port_abstract_methods() -> None:
    """Verify abstract methods on QualityAuditorPort."""
    expected = {
        "audit_complexity",
        "audit_parity",
        "audit_statements",
        "fix_statements",
        "run_sanity",
    }
    abstracts = QualityAuditorPort.__abstractmethods__
    diff = expected.difference(abstracts)
    assert len(diff) == 0
