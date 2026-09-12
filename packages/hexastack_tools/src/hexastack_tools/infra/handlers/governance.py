"""CQRS Command Handlers for repository governance and sanity verification.

Notes/Architectural Intent:
    Decouples verification business logic from execution mechanisms. Each check
    is a discrete CommandHandler, and RunSanityCheckHandler composites sub-checks
    by dispatching sub-commands directly across the CommandBusPort.
"""

from __future__ import annotations

import time

from hexastack_cqrs.ports.buses import CommandBusPort
from hexastack_tools.domain.governance import (
    AuditComplexityCommand,
    CheckAllStatementsCommand,
    CheckResult,
    CheckStatus,
    CheckTestParityCommand,
    RunLinterCommand,
    RunPytestCommand,
    RunSanityCheckCommand,
    RunTypecheckCommand,
    SanityCheckReport,
    SanityTarget,
)
from hexastack_tools.ports.governance import ToolRunnerPort

__all__ = [
    "AuditComplexityHandler",
    "CheckAllStatementsHandler",
    "CheckTestParityHandler",
    "RunLinterHandler",
    "RunPytestHandler",
    "RunSanityCheckHandler",
    "RunTypecheckHandler",
]


class RunLinterHandler:
    """Handler executing lint and formatting checks via ToolRunnerPort."""

    def __init__(self, runner: ToolRunnerPort) -> None:
        """Initialize with tool runner port.

        Args:
            runner: Concrete ToolRunnerPort implementation.
        """
        self._runner = runner

    def handle(self, command: RunLinterCommand) -> CheckResult:
        """Execute linter check.

        Args:
            command: RunLinterCommand specification.

        Returns:
            CheckResult outcome.
        """
        return self._runner.run_ruff(
            command.paths, command.target_name, fix=command.fix
        )


class RunTypecheckHandler:
    """Handler executing static typechecks via ToolRunnerPort."""

    def __init__(self, runner: ToolRunnerPort) -> None:
        """Initialize with tool runner port.

        Args:
            runner: Concrete ToolRunnerPort implementation.
        """
        self._runner = runner

    def handle(self, command: RunTypecheckCommand) -> CheckResult:
        """Execute typecheck.

        Args:
            command: RunTypecheckCommand specification.

        Returns:
            CheckResult outcome.
        """
        return self._runner.run_ty(command.paths, command.target_name)


class AuditComplexityHandler:
    """Handler auditing cognitive complexity via ToolRunnerPort."""

    def __init__(self, runner: ToolRunnerPort) -> None:
        """Initialize with tool runner port.

        Args:
            runner: Concrete ToolRunnerPort implementation.
        """
        self._runner = runner

    def handle(self, command: AuditComplexityCommand) -> CheckResult:
        """Execute complexity audit.

        Args:
            command: AuditComplexityCommand specification.

        Returns:
            CheckResult outcome.
        """
        return self._runner.run_complexipy(
            command.paths, command.target_name, max_complexity=command.max_complexity
        )


class CheckAllStatementsHandler:
    """Handler verifying __all__ integrity via ToolRunnerPort."""

    def __init__(self, runner: ToolRunnerPort) -> None:
        """Initialize with tool runner port.

        Args:
            runner: Concrete ToolRunnerPort implementation.
        """
        self._runner = runner

    def handle(self, command: CheckAllStatementsCommand) -> CheckResult:
        """Execute __all__ check.

        Args:
            command: CheckAllStatementsCommand specification.

        Returns:
            CheckResult outcome.
        """
        return self._runner.run_all_statements(
            command.paths, command.target_name, fix=command.fix
        )


class CheckTestParityHandler:
    """Handler validating unit test symmetry via ToolRunnerPort."""

    def __init__(self, runner: ToolRunnerPort) -> None:
        """Initialize with tool runner port.

        Args:
            runner: Concrete ToolRunnerPort implementation.
        """
        self._runner = runner

    def handle(self, command: CheckTestParityCommand) -> CheckResult:
        """Execute parity audit.

        Args:
            command: CheckTestParityCommand specification.

        Returns:
            CheckResult outcome.
        """
        return self._runner.run_test_parity(command.target, command.repo_root)


class RunPytestHandler:
    """Handler executing test suites via ToolRunnerPort."""

    def __init__(self, runner: ToolRunnerPort) -> None:
        """Initialize with tool runner port.

        Args:
            runner: Concrete ToolRunnerPort implementation.
        """
        self._runner = runner

    def handle(self, command: RunPytestCommand) -> CheckResult:
        """Execute test runner.

        Args:
            command: RunPytestCommand specification.

        Returns:
            CheckResult outcome.
        """
        return self._runner.run_pytest(
            command.target, command.repo_root, skip=command.skip
        )


class RunSanityCheckHandler:
    """Composite handler orchestrating complete sanity check battery across targets.

    Notes/Architectural Intent:
        Dispatches individual domain commands across the CommandBusPort, compositing
        results and calculating total runtime and overall exit status.
    """

    def __init__(self, bus: CommandBusPort) -> None:
        """Initialize composite handler with CommandBusPort.

        Args:
            bus: CommandBusPort instance for sub-command dispatch.
        """
        self._bus = bus

    def _execute_target_checks(
        self,
        target: SanityTarget,
        command: RunSanityCheckCommand,
    ) -> list[CheckResult]:
        """Execute standard check battery for a single target."""
        results: list[CheckResult] = []
        combined_paths = target.src_paths + target.test_paths

        # 1. Lint / Format
        results.append(
            self._bus.dispatch(
                RunLinterCommand(
                    paths=combined_paths,
                    target_name=target.name,
                    fix=command.fix,
                )
            )
        )

        # 2. Ty Typecheck
        results.append(
            self._bus.dispatch(
                RunTypecheckCommand(
                    paths=combined_paths,
                    target_name=target.name,
                )
            )
        )

        # 3. Complexity
        results.append(
            self._bus.dispatch(
                AuditComplexityCommand(
                    paths=target.src_paths,
                    target_name=target.name,
                    max_complexity=command.max_complexity,
                )
            )
        )

        # 4. __all__ Integrity
        results.append(
            self._bus.dispatch(
                CheckAllStatementsCommand(
                    paths=target.src_paths,
                    target_name=target.name,
                    fix=command.fix,
                )
            )
        )

        # 5. Test Parity
        if target.kind == "package":
            results.append(
                self._bus.dispatch(
                    CheckTestParityCommand(
                        target=target,
                        repo_root=command.repo_root,
                    )
                )
            )

        # 6. Pytest
        results.append(
            self._bus.dispatch(
                RunPytestCommand(
                    target=target,
                    repo_root=command.repo_root,
                    skip=command.skip_tests,
                )
            )
        )

        return results

    def handle(self, command: RunSanityCheckCommand) -> SanityCheckReport:
        """Execute composite sanity check battery.

        Args:
            command: RunSanityCheckCommand specification.

        Returns:
            SanityCheckReport aggregate.
        """
        start = time.perf_counter()
        all_results: list[CheckResult] = []

        for target in command.targets:
            all_results.extend(self._execute_target_checks(target, command))

        total_duration = time.perf_counter() - start
        has_failure = any(r.status == CheckStatus.FAIL for r in all_results)
        exit_code = 1 if has_failure else 0

        return SanityCheckReport(
            results=tuple(all_results),
            total_duration=total_duration,
            exit_code=exit_code,
        )
