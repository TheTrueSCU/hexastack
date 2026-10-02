"""Abstract port for OpenSSF Best Practices auditing and compliance gating.

Notes/Architectural Intent:
    Defines the contract for OpenSSF Best Practices badge auditing according to
    hexagonal principles. Implementations wrap hexaqual's OpenSSF infra layer,
    keeping the domain and CQRS handlers independent of the concrete evaluation
    engine.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from hexastack_qual.domain.models import (
        OpenSsfAuditSummary,
        OpenSsfComplianceResult,
    )


class OpenSsfAuditorPort(ABC):
    """Abstract port for OpenSSF Best Practices auditing and CI compliance gating.

    Notes/Architectural Intent:
        Decouples CQRS handlers, MCP tools, and NiceGUI panels from hexaqual's
        concrete OpenSSF engine. Enables in-memory stub implementations for
        hermetic unit testing without network calls to bestpractices.coreinfrastructure.org.
    """

    @abstractmethod
    def audit_openssf(
        self,
        project_url: str | None = None,
    ) -> OpenSsfAuditSummary:
        """Evaluate local OpenSSF Best Practices posture via heuristic analysis.

        Args:
            project_url: Optional repository URL for badge context. If None,
                resolved from local git remote origin.

        Returns:
            OpenSsfAuditSummary with per-tier scores and unmet criteria list.

        Raises:
            QualityError: If the local heuristic evaluation fails.

        Notes/Architectural Intent:
            Delegates to hexaqual's evaluate_local_heuristics() and
            audit_project_posture() infra functions. No network call to the
            OpenSSF badge API is made — posture is assessed from local
            repository artifacts (CI workflow files, SECURITY.md, codecov.yml,
            signed commits, etc.).
        """

    @abstractmethod
    def check_openssf_compliance(
        self,
        tier: str = "passing",
        min_score: float | None = None,
    ) -> OpenSsfComplianceResult:
        """Verify that the project meets a required OpenSSF badge tier for CI gating.

        Args:
            tier: Required badge tier ('passing', 'silver', or 'gold').
            min_score: Optional minimum percentage score override. If None,
                defaults to 100.0 for the specified tier.

        Returns:
            OpenSsfComplianceResult with is_compliant flag and failure_reasons.

        Raises:
            QualityError: If the compliance check cannot be executed.

        Notes/Architectural Intent:
            Wraps hexaqual's verify_openssf_compliance() infra function.
            Designed for use as a blocking CI gate — callers should treat
            is_compliant=False as a build failure signal.
        """

    @abstractmethod
    def generate_openssf_checklist(
        self,
        tier: str = "passing",
        project_url: str | None = None,
    ) -> str:
        """Generate a Markdown checklist of OpenSSF criteria for a target tier.

        Args:
            tier: Target badge tier ('passing', 'silver', or 'gold').
            project_url: Optional repository URL for badge link context.

        Returns:
            Markdown-formatted checklist string with checkbox status per criterion.

        Raises:
            QualityError: If checklist generation fails.

        Notes/Architectural Intent:
            Delegates to hexaqual's generate_checklist() and
            format_checklist_markdown() infra functions. Output is suitable
            for direct insertion into GitHub issues, PR descriptions, or the
            NiceGUI DevTools OpenSSF panel.
        """


__all__ = [
    "OpenSsfAuditorPort",
]
