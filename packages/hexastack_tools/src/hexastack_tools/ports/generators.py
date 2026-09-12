"""Port interfaces for architecture and documentation generators.

Notes/Architectural Intent:
    Defines abstract presentation boundaries for pydeps diagrams, USAGE.md
    documentation generators, and pytest-archon scaffolding reports.
"""

from __future__ import annotations

from abc import ABC, abstractmethod

from hexastack_tools.domain.generators import (
    ArchonReport,
    PydepsReport,
    UsageDocsReport,
)


class GeneratorPresenterPort(ABC):
    """Abstract port defining presentation contracts for generators and catalog tools."""

    @abstractmethod
    def present_pydeps(self, report: PydepsReport) -> int:
        """Present results of pydeps architecture dependency diagram generation.

        Args:
            report: PydepsReport containing generated diagram paths and status.

        Returns:
            Exit code (0 for success, non-zero for failure).

        Notes/Architectural Intent:
            Renders diagram generation summaries in interactive terminal tables,
            JSON records, or markdown summaries.
        """
        raise NotImplementedError

    @abstractmethod
    def present_usage_docs(self, report: UsageDocsReport) -> int:
        """Present results of USAGE.md verification or updates.

        Args:
            report: UsageDocsReport containing freshness evaluation and diffs.

        Returns:
            Exit code (0 for up-to-date/fixed, 1 if stale during check).

        Notes/Architectural Intent:
            Formats documentation status for developer feedback or pre-commit
            automated checks.
        """
        raise NotImplementedError

    @abstractmethod
    def present_archon(self, report: ArchonReport) -> int:
        """Present results of pytest-archon test scaffolding.

        Args:
            report: ArchonReport containing scaffolded test file paths.

        Returns:
            Exit code (0 for success, non-zero for failure).

        Notes/Architectural Intent:
            Outputs created and skipped architecture test specification files.
        """
        raise NotImplementedError


__all__ = [
    "GeneratorPresenterPort",
]
