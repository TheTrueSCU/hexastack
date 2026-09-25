"""Unit tests for QualityAuditorPort interface.

Notes/Architectural Intent:
    Ensures QualityAuditorPort cannot be instantiated directly and that
    concrete subclasses correctly satisfy abstract method requirements.
"""

from __future__ import annotations

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
        QualityAuditorPort()  # type: ignore[abstract]


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
