"""Port contracts for tooling runners and governance presentation.

Notes/Architectural Intent:
    Defines abstract interfaces separating test execution, static analysis,
    and dashboard presentation from specific third-party tools or CLI runners.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path

from hexastack_tools.domain.governance import (
    CheckResult,
    SanityCheckReport,
    SanityTarget,
)

__all__ = [
    "GovernancePresenterPort",
    "ToolRunnerPort",
]


class ToolRunnerPort(ABC):
    """Abstract port for executing code quality and governance tools."""

    @abstractmethod
    def run_ruff(
        self,
        paths: tuple[Path, ...],
        target_name: str,
        fix: bool = False,
    ) -> CheckResult:
        """Run Ruff linter and formatter.

        Args:
            paths: Target paths to audit.
            target_name: Human-readable target name.
            fix: Whether to automatically fix violations.

        Returns:
            CheckResult with execution status and diagnostics.
        """

    @abstractmethod
    def run_ty(
        self,
        paths: tuple[Path, ...],
        target_name: str,
    ) -> CheckResult:
        """Run Ty static type checker.

        Args:
            paths: Target paths to typecheck.
            target_name: Human-readable target name.

        Returns:
            CheckResult with type diagnostics.
        """

    @abstractmethod
    def run_complexipy(
        self,
        paths: tuple[Path, ...],
        target_name: str,
        max_complexity: int = 25,
    ) -> CheckResult:
        """Audit cognitive complexity using complexipy.

        Args:
            paths: Target paths to inspect.
            target_name: Human-readable target name.
            max_complexity: Cognitive complexity ceiling.

        Returns:
            CheckResult with complexity status.
        """

    @abstractmethod
    def run_all_statements(
        self,
        paths: tuple[Path, ...],
        target_name: str,
        fix: bool = False,
    ) -> CheckResult:
        """Verify __all__ integrity and sorting.

        Args:
            paths: Target source paths.
            target_name: Human-readable target name.
            fix: Whether to auto-sort and format __all__.

        Returns:
            CheckResult with sorting diagnostics.
        """

    @abstractmethod
    def run_test_parity(
        self,
        target: SanityTarget,
        repo_root: Path,
    ) -> CheckResult:
        """Validate 1:1 unit test parity and __init__.py symmetry.

        Args:
            target: Target component to audit.
            repo_root: Repository root path.

        Returns:
            CheckResult with parity diagnostics.
        """

    @abstractmethod
    def run_pytest(
        self,
        target: SanityTarget,
        repo_root: Path,
        skip: bool = False,
    ) -> CheckResult:
        """Run targeted pytest test suite.

        Args:
            target: Target component to test.
            repo_root: Repository root path.
            skip: Whether to skip test suite execution.

        Returns:
            CheckResult with test outcomes.
        """


class GovernancePresenterPort(ABC):
    """Abstract port for presenting governance reports and dashboards."""

    @abstractmethod
    def present_sanity_dashboard(self, report: SanityCheckReport) -> int:
        """Render sanity check results table and diagnostics.

        Args:
            report: Aggregated SanityCheckReport object.

        Returns:
            Process exit code (0 for pass, 1 for failure).
        """
