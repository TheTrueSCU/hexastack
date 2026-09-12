"""Port interfaces for refactoring and publishing presenters.

Notes/Architectural Intent:
    Defines abstract presentation boundaries for code alphabetization and
    Medium/DEV.to publication pipelines.
"""

from __future__ import annotations

from abc import ABC, abstractmethod

from hexastack_tools.domain.refactoring import (
    AlphabetizeCodeReport,
    MediumPublishReport,
)


class RefactoringPresenterPort(ABC):
    """Abstract port defining presentation contracts for refactoring and publishing tools."""

    @abstractmethod
    def present_alphabetize(self, report: AlphabetizeCodeReport) -> int:
        """Present results of function and method alphabetization.

        Args:
            report: AlphabetizeCodeReport containing modified and unchanged files.

        Returns:
            Exit code (0 for success, 1 for errors).

        Notes/Architectural Intent:
            Renders formatted console output or structured JSON records.
        """
        raise NotImplementedError

    @abstractmethod
    def present_medium_publish(self, report: MediumPublishReport) -> int:
        """Present results of Medium/DEV.to article publication.

        Args:
            report: MediumPublishReport containing publication outcomes.

        Returns:
            Exit code (0 for success, 1 for errors).

        Notes/Architectural Intent:
            Formats publication results and syndication links.
        """
        raise NotImplementedError


__all__ = [
    "RefactoringPresenterPort",
]
