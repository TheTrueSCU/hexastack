"""Abstract port for GitHub PR health diagnostics and test impact analysis.

Notes/Architectural Intent:
    Defines the contract for querying pull request checks, CodeQL security
    findings, and git-diff impacted test selectors.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from hexastack_qual.domain.models import PrHealthSummary


class PrDiagnosticPort(ABC):
    """Abstract port for inspecting PR health and computing test impact.

    Notes/Architectural Intent:
        Decouples GitHub API and git diff inspection from callers.
    """

    @abstractmethod
    def get_pr_health(self, pr_number: int) -> PrHealthSummary:
        """Query status checks, CodeQL alerts, and review threads for a PR.

        Args:
            pr_number: The GitHub pull request number.

        Returns:
            PrHealthSummary containing status metrics.

        Raises:
            QualityError: If PR inspection fails.
        """

    @abstractmethod
    def get_test_impact(self, base_ref: str = "origin/main") -> list[str]:
        """Compute test paths impacted by changes relative to base_ref.

        Args:
            base_ref: Git reference or branch to compare against.

        Returns:
            List of impacted test file paths or package names.

        Raises:
            QualityError: If git diff or impact analysis fails.
        """


__all__ = [
    "PrDiagnosticPort",
]
