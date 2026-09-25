"""Abstract port for mutation testing and surviving mutant inspection.

Notes/Architectural Intent:
    Defines the contract for executing mutation testing and retrieving classified
    surviving mutant reports.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from hexastack_qual.domain.models import MutantReport


class MutationInspectorPort(ABC):
    """Abstract port for mutation testing execution and triage analysis.

    Notes/Architectural Intent:
        Abstracts the underlying mutmut runner and mutant classifier, allowing
        mocked verification in tests and flexible engine upgrades.
    """

    @abstractmethod
    def inspect_surviving_mutants(
        self,
        package: str | None = None,
        actionable_only: bool = True,
    ) -> MutantReport:
        """Retrieve surviving mutants and triage classifications.

        Args:
            package: Optional target package name.
            actionable_only: If True, filters only critical actionable mutants.

        Returns:
            MutantReport summary containing surviving mutants and scores.

        Raises:
            QualityError: If mutant inspection fails.
        """

    @abstractmethod
    def run_mutation_testing(
        self,
        package: str | None = None,
        reset: bool = False,
    ) -> MutantReport:
        """Execute mutation testing across target components.

        Args:
            package: Optional target package name.
            reset: Whether to clear existing mutation cache before running.

        Returns:
            MutantReport summary with outcome scores.

        Raises:
            QualityError: If mutation testing runner fails.
        """


__all__ = [
    "MutationInspectorPort",
]
