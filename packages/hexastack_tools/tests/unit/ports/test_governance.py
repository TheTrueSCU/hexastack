"""Unit tests for governance port interfaces.

Notes/Architectural Intent:
    Verifies that ToolRunnerPort and GovernancePresenterPort enforce method
    signatures and prevent direct instantiation of abstract classes.
"""

from pathlib import Path

import pytest

from hexastack_tools.domain.governance import (
    CheckResult,
    CheckStatus,
    SanityCheckReport,
    SanityTarget,
)
from hexastack_tools.ports.governance import (
    GovernancePresenterPort,
    ToolRunnerPort,
)


def test_tool_runner_port_is_abstract():
    """Verify ToolRunnerPort cannot be instantiated directly."""
    with pytest.raises(TypeError):
        ToolRunnerPort()  # type: ignore[abstract]


def test_governance_presenter_port_is_abstract():
    """Verify GovernancePresenterPort cannot be instantiated directly."""
    with pytest.raises(TypeError):
        GovernancePresenterPort()  # type: ignore[abstract]


def test_concrete_tool_runner_implementation():
    """Verify a concrete ToolRunnerPort implementation satisfies the contract."""

    class DummyRunner(ToolRunnerPort):
        def run_ruff(
            self, paths: tuple[Path, ...], target_name: str, fix: bool = False
        ) -> CheckResult:
            return CheckResult("Ruff", target_name, CheckStatus.PASS, 0.01)

        def run_ty(self, paths: tuple[Path, ...], target_name: str) -> CheckResult:
            return CheckResult("Ty", target_name, CheckStatus.PASS, 0.01)

        def run_complexipy(
            self,
            paths: tuple[Path, ...],
            target_name: str,
            max_complexity: int = 25,
        ) -> CheckResult:
            return CheckResult("Complexipy", target_name, CheckStatus.PASS, 0.01)

        def run_all_statements(
            self, paths: tuple[Path, ...], target_name: str, fix: bool = False
        ) -> CheckResult:
            return CheckResult("AllStatements", target_name, CheckStatus.PASS, 0.01)

        def run_test_parity(self, target: SanityTarget, repo_root: Path) -> CheckResult:
            return CheckResult("Parity", target.name, CheckStatus.PASS, 0.01)

        def run_pytest(
            self, target: SanityTarget, repo_root: Path, skip: bool = False
        ) -> CheckResult:
            return CheckResult("Pytest", target.name, CheckStatus.PASS, 0.01)

    runner = DummyRunner()
    res = runner.run_ruff((Path(),), "dummy")
    assert res.status == CheckStatus.PASS


def test_concrete_presenter_implementation():
    """Verify a concrete GovernancePresenterPort implementation satisfies the contract."""

    class DummyPresenter(GovernancePresenterPort):
        def present_sanity_dashboard(self, report: SanityCheckReport) -> int:
            return report.exit_code

        def present_all_statements(
            self,
            errors: list[str],
            modified_count: int | None = None,
        ) -> int:
            return 1 if errors else 0

        def present_test_parity(
            self,
            init_errors: list[str],
            symmetry_errors: list[str],
        ) -> int:
            return 1 if (init_errors or symmetry_errors) else 0

    presenter = DummyPresenter()
    report = SanityCheckReport(results=(), total_duration=0.0, exit_code=0)
    assert presenter.present_sanity_dashboard(report) == 0
    assert presenter.present_all_statements([]) == 0
    assert presenter.present_test_parity([], []) == 0
