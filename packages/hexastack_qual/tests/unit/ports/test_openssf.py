"""Unit tests for OpenSsfAuditorPort abstract contract.

Notes/Architectural Intent:
    Validates the abstract method signatures and that the port cannot be
    instantiated directly. Uses a stub implementation to verify the contract
    is callable with expected signatures.
"""

from __future__ import annotations

import pytest
from hexastack_qual.domain.models import (
    OpenSsfAuditSummary,
    OpenSsfComplianceResult,
    OpenSsfCriterionResult,
)
from hexastack_qual.ports.openssf import OpenSsfAuditorPort


class _StubOpenSsfAuditor(OpenSsfAuditorPort):
    """Minimal stub implementation of OpenSsfAuditorPort for contract testing."""

    def audit_openssf(self, project_url: str | None = None) -> OpenSsfAuditSummary:
        return OpenSsfAuditSummary(
            project_url=project_url or "https://github.com/test/repo",
            passing_score=80.0,
            silver_score=60.0,
            gold_score=40.0,
            met_count=8,
            total_count=10,
            unmet_criteria=[
                OpenSsfCriterionResult(
                    criterion_id="dco",
                    title="DCO sign-off",
                    tier="passing",
                    met=False,
                    notes="No DCO enforcement found",
                ),
            ],
        )

    def check_openssf_compliance(
        self,
        tier: str = "passing",
        min_score: float | None = None,
    ) -> OpenSsfComplianceResult:
        threshold = min_score if min_score is not None else 100.0
        return OpenSsfComplianceResult(
            is_compliant=False,
            required_tier=tier,
            achieved_score=80.0,
            required_score=threshold,
            failure_reasons=["dco", "sha-pinning"],
        )

    def generate_openssf_checklist(
        self,
        tier: str = "passing",
        project_url: str | None = None,
    ) -> str:
        return f"## OpenSSF {tier.title()} Checklist\n- [ ] DCO sign-off\n"


class TestOpenSsfAuditorPortContract:
    """Validates OpenSsfAuditorPort ABC contract enforcement and stub correctness."""

    def test_cannot_instantiate_abstract_port(self) -> None:
        """Port must be abstract and raise TypeError on direct instantiation."""
        with pytest.raises(TypeError):
            OpenSsfAuditorPort()  # ty: ignore[call-non-callable]

    def test_stub_audit_openssf_returns_summary(self) -> None:
        """audit_openssf() returns an OpenSsfAuditSummary with expected fields."""
        auditor = _StubOpenSsfAuditor()
        result = auditor.audit_openssf(project_url="https://github.com/test/repo")

        assert result.project_url == "https://github.com/test/repo"
        assert isinstance(result.passing_score, float)
        assert isinstance(result.unmet_criteria, list)
        assert len(result.unmet_criteria) == 1
        assert result.unmet_criteria[0].criterion_id == "dco"

    def test_stub_audit_openssf_resolves_url_when_none(self) -> None:
        """audit_openssf() with project_url=None falls back to a resolved URL."""
        auditor = _StubOpenSsfAuditor()
        result = auditor.audit_openssf(project_url=None)

        assert result.project_url == "https://github.com/test/repo"

    def test_stub_check_compliance_returns_non_compliant(self) -> None:
        """check_openssf_compliance() returns is_compliant=False with failure_reasons."""
        auditor = _StubOpenSsfAuditor()
        result = auditor.check_openssf_compliance(tier="passing")

        assert result.is_compliant is False
        assert result.required_tier == "passing"
        assert "dco" in result.failure_reasons
        assert result.achieved_score < result.required_score

    def test_stub_check_compliance_uses_min_score_override(self) -> None:
        """check_openssf_compliance() passes min_score override to result."""
        auditor = _StubOpenSsfAuditor()
        result = auditor.check_openssf_compliance(tier="silver", min_score=75.0)

        assert result.required_score == 75.0
        assert result.required_tier == "silver"

    def test_stub_generate_checklist_returns_markdown(self) -> None:
        """generate_openssf_checklist() returns a non-empty Markdown string."""
        auditor = _StubOpenSsfAuditor()
        checklist = auditor.generate_openssf_checklist(tier="passing")

        assert isinstance(checklist, str)
        assert len(checklist) > 0
        assert "passing" in checklist.lower() or "Passing" in checklist

    def test_stub_generate_checklist_tier_propagated(self) -> None:
        """generate_openssf_checklist() propagates tier argument."""
        auditor = _StubOpenSsfAuditor()
        gold_checklist = auditor.generate_openssf_checklist(tier="gold")

        assert "gold" in gold_checklist.lower() or "Gold" in gold_checklist


__all__ = [
    "TestOpenSsfAuditorPortContract",
]
