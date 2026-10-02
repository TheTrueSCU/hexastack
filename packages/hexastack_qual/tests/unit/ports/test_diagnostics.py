"""Unit tests for PrDiagnosticPort interface.

Notes/Architectural Intent:
    Ensures PrDiagnosticPort cannot be instantiated directly and that
    concrete subclasses fulfill abstract requirements.
"""

from __future__ import annotations

import pytest
from hexastack_qual.domain.models import PrHealthSummary
from hexastack_qual.ports.diagnostics import PrDiagnosticPort


class DummyDiagnostics(PrDiagnosticPort):
    """Concrete dummy implementation for interface testing."""

    def get_pr_health(self, pr_number: int) -> PrHealthSummary:
        return PrHealthSummary(
            pr_number=pr_number,
            title="dummy",
            state="open",
            ci_status="success",
        )

    def get_test_impact(self, base_ref: str = "origin/main") -> list[str]:
        return ["packages/hexastack_core/tests/unit/test_foo.py"]


def test_pr_diagnostic_port_cannot_instantiate_abstract() -> None:
    """Ensure abstract port cannot be instantiated directly."""
    with pytest.raises(TypeError):
        PrDiagnosticPort()  # type: ignore[abstract]


def test_concrete_diagnostics_satisfies_contract() -> None:
    """Ensure concrete diagnostics satisfies port interface."""
    diag = DummyDiagnostics()
    summary = diag.get_pr_health(99)
    impact = diag.get_test_impact()

    assert summary.pr_number == 99
    assert len(impact) == 1
