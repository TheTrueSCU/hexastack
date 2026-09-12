"""Port interfaces for security analysis, fuzzing, and snapshot presenters.

Notes/Architectural Intent:
    Defines abstract presentation boundaries for local CodeQL scanning,
    Atheris/OWASP fuzzing harnesses, and inline-snapshot updates.
"""

from __future__ import annotations

from abc import ABC, abstractmethod

from hexastack_tools.domain.analysis import (
    CodeQlScanReport,
    FuzzRunReport,
    InlineSnapshotsReport,
)


class AnalysisPresenterPort(ABC):
    """Abstract port defining presentation contracts for static analysis and security tools."""

    @abstractmethod
    def present_codeql(self, report: CodeQlScanReport) -> int:
        """Present results of local CodeQL SAST scanning.

        Args:
            report: CodeQlScanReport containing analysis outcome and findings.

        Returns:
            Exit code (0 for clean scan, 1 for errors or critical findings).

        Notes/Architectural Intent:
            Formats CodeQL database analysis results into terminal panels, JSON,
            or CI markdown summaries.
        """
        raise NotImplementedError

    @abstractmethod
    def present_fuzz(self, report: FuzzRunReport) -> int:
        """Present results of fuzzing test harnesses.

        Args:
            report: FuzzRunReport containing metrics per fuzzing target.

        Returns:
            Exit code (0 if all harnesses passed, 1 if crashes or ReDoS occurred).

        Notes/Architectural Intent:
            Displays run iterations, durations, and crash/ReDoS metrics.
        """
        raise NotImplementedError

    @abstractmethod
    def present_inline_snapshots(self, report: InlineSnapshotsReport) -> int:
        """Present results of inline snapshot updates.

        Args:
            report: InlineSnapshotsReport containing processed targets.

        Returns:
            Exit code (0 for success, non-zero for test failures).

        Notes/Architectural Intent:
            Formats snapshot update execution status.
        """
        raise NotImplementedError


__all__ = [
    "AnalysisPresenterPort",
]
