"""Abstract port for codebase quality, complexity, and statement auditing.

Notes/Architectural Intent:
    Defines the contract for quality auditing operations according to hexagonal
    principles. Implementations wrap concrete inspection engines (e.g. Hexaqual).
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from hexastack_qual.domain.models import (
        ComplexityMetric,
        ParityFinding,
        QualityScorecard,
        StatementFinding,
    )


class QualityAuditorPort(ABC):
    """Abstract port for codebase quality, symmetry, and complexity audits.

    Notes/Architectural Intent:
        Decouples domain services, CQRS handlers, and MCP tools from the
        concrete hexaqual implementation or underlying linters.
    """

    @abstractmethod
    def audit_complexity(
        self,
        package: str | None = None,
        max_complexity: int = 25,
    ) -> list[ComplexityMetric]:
        """Audit cognitive complexity across target modules.

        Args:
            package: Optional target package name. If None, audits workspace.
            max_complexity: Maximum allowed cognitive complexity threshold.

        Returns:
            List of ComplexityMetric objects identifying functions.

        Raises:
            QualityError: If complexity auditing fails.
        """

    @abstractmethod
    def audit_parity(
        self,
        package: str | None = None,
    ) -> list[ParityFinding]:
        """Audit 1:1 test symmetry between src/ and tests/unit/.

        Args:
            package: Optional target package name.

        Returns:
            List of ParityFinding objects reporting symmetry status.

        Raises:
            QualityError: If parity inspection fails.
        """

    @abstractmethod
    def audit_statements(
        self,
        package: str | None = None,
    ) -> list[StatementFinding]:
        """Verify sorting and deduplication of __all__ export statements.

        Args:
            package: Optional target package name.

        Returns:
            List of StatementFinding objects identifying invalid files.

        Raises:
            QualityError: If statement auditing fails.
        """

    @abstractmethod
    def fix_statements(
        self,
        package: str | None = None,
    ) -> int:
        """Auto-format and sort __all__ lists across modules.

        Args:
            package: Optional target package name.

        Returns:
            Count of files modified.

        Raises:
            QualityError: If auto-formatting fails.
        """

    @abstractmethod
    def run_sanity(
        self,
        package: str | None = None,
        skip_tests: bool = True,
    ) -> QualityScorecard:
        """Execute a full sanity check suite across target components.

        Args:
            package: Optional target package name.
            skip_tests: Whether to skip long-running unit test suites.

        Returns:
            QualityScorecard aggregate summarizing check outcomes.

        Raises:
            QualityError: If sanity suite execution fails.
        """


__all__ = [
    "QualityAuditorPort",
]
