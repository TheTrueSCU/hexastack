"""Command handlers for mutation testing, test boundary audits, and test impact analysis.

Notes/Architectural Intent:
    Executes testing commands by delegating to TestingRunnerPort adapter and
    synthesizing domain reports for presentation.
"""

from __future__ import annotations

import re

from hexastack_tools.domain.testing import (
    AuditTestBoundariesCommand,
    AuditTestRedundancyCommand,
    BoundaryAuditItem,
    BoundaryAuditReport,
    ImpactedTestsReport,
    InspectMutationCacheCommand,
    MutantCategory,
    MutantRecord,
    MutationAuditReport,
    MutationPackageSummary,
    RedundancyAuditReport,
    RunImpactedTestsCommand,
    RunMutationTestsCommand,
)
from hexastack_tools.ports.testing import TestingRunnerPort
from hexastack_tools.utils.mutmut import classify_mutant_line
from hexastack_tools.utils.workspace import (
    VALID_PACKAGES,
    get_package_directory,
)

__all__ = [
    "AuditTestBoundariesHandler",
    "AuditTestRedundancyHandler",
    "InspectMutationCacheHandler",
    "RunImpactedTestsHandler",
    "RunMutationTestsHandler",
]


class RunMutationTestsHandler:
    """Handler executing mutmut mutation testing across targeted or all packages."""

    def __init__(self, runner: TestingRunnerPort) -> None:
        """Initialize handler with TestingRunnerPort adapter.

        Args:
            runner: TestingRunnerPort adapter instance.
        """
        self._runner = runner

    def handle(self, command: RunMutationTestsCommand) -> int:
        """Run mutation testing for package(s).

        Args:
            command: RunMutationTestsCommand instance.

        Returns:
            Exit code of mutation testing process.
        """
        if command.package:
            pkg_dir = get_package_directory(command.package)
            return self._runner.run_mutmut(pkg_dir, reset_cache=command.reset_cache)

        if command.all_packages:
            exit_code = 0
            for pkg_name in sorted(VALID_PACKAGES):
                pkg_dir = get_package_directory(pkg_name)
                code = self._runner.run_mutmut(pkg_dir, reset_cache=command.reset_cache)
                if code != 0:
                    exit_code = code
            return exit_code

        return 0


class InspectMutationCacheHandler:
    """Handler inspecting and classifying surviving mutants in .mutmut-cache SQLite database."""

    def __init__(self, runner: TestingRunnerPort) -> None:
        """Initialize handler with TestingRunnerPort adapter.

        Args:
            runner: TestingRunnerPort adapter instance.
        """
        self._runner = runner

    def handle(self, command: InspectMutationCacheCommand) -> MutationAuditReport:
        """Inspect and categorize surviving mutants from cache database.

        Args:
            command: InspectMutationCacheCommand instance.

        Returns:
            MutationAuditReport domain model.
        """
        records = self._runner.read_mutmut_cache(
            command.cache_file, package_filter=command.package
        )
        if not records:
            return MutationAuditReport(summaries=(), actionable_mutants=())

        package_stats: dict[str, dict[str, int]] = {}
        actionable_mutants: list[MutantRecord] = []

        for rec in records:
            fname = rec["filename"]
            line_str = rec["line"]
            m_id = rec["id"]

            match = re.search(r"packages/([^/]+)/", fname)
            pkg = match.group(1) if match else "hexastack"
            if pkg not in package_stats:
                package_stats[pkg] = {
                    "total": 0,
                    "critical": 0,
                    "equivalent": 0,
                    "ignorable": 0,
                }

            category_str, rationale = classify_mutant_line(line_str, fname)
            cat = MutantCategory(category_str)
            package_stats[pkg]["total"] += 1
            package_stats[pkg][category_str.lower()] += 1

            if command.actionable_only and cat == MutantCategory.CRITICAL:
                covering_tests: tuple[str, ...] = ()
                if command.correlate_coverage and command.coverage_file:
                    covering_tests = tuple(
                        self._runner.get_tests_covering_line(
                            fname, 1, command.coverage_file
                        )
                    )

                actionable_mutants.append(
                    MutantRecord(
                        id=m_id,
                        filename=fname,
                        line_number=1,
                        line_content=line_str.strip(),
                        category=cat,
                        rationale=rationale,
                        covering_tests=covering_tests,
                    )
                )

        summaries = tuple(
            MutationPackageSummary(
                package_name=pkg,
                total=stats["total"],
                critical=stats["critical"],
                equivalent=stats["equivalent"],
                ignorable=stats["ignorable"],
            )
            for pkg, stats in package_stats.items()
        )

        return MutationAuditReport(
            summaries=summaries,
            actionable_mutants=tuple(actionable_mutants),
        )


class AuditTestBoundariesHandler:
    """Handler auditing test execution contexts in .coverage for layer boundary leaks."""

    def __init__(self, runner: TestingRunnerPort) -> None:
        """Initialize handler with TestingRunnerPort adapter.

        Args:
            runner: TestingRunnerPort adapter instance.
        """
        self._runner = runner

    def handle(self, command: AuditTestBoundariesCommand) -> BoundaryAuditReport:
        """Audit layer boundaries in test executions.

        Args:
            command: AuditTestBoundariesCommand instance.

        Returns:
            BoundaryAuditReport domain model.
        """
        leaks = self._runner.audit_layer_boundary_leaks(command.coverage_file)
        return BoundaryAuditReport(
            leaks=tuple(BoundaryAuditItem(c, f) for c, f in leaks)
        )


class AuditTestRedundancyHandler:
    """Handler auditing .coverage branch execution arcs for redundant tests."""

    def __init__(self, runner: TestingRunnerPort) -> None:
        """Initialize handler with TestingRunnerPort adapter.

        Args:
            runner: TestingRunnerPort adapter instance.
        """
        self._runner = runner

    def handle(self, command: AuditTestRedundancyCommand) -> RedundancyAuditReport:
        """Audit redundant tests in test suite.

        Args:
            command: AuditTestRedundancyCommand instance.

        Returns:
            RedundancyAuditReport domain model.
        """
        tests = self._runner.audit_redundant_tests(command.coverage_file)
        return RedundancyAuditReport(redundant_tests=tuple(tests))


class RunImpactedTestsHandler:
    """Handler executing Test Impact Analysis (TIA) and targeted pytest executions."""

    def __init__(self, runner: TestingRunnerPort) -> None:
        """Initialize handler with TestingRunnerPort adapter.

        Args:
            runner: TestingRunnerPort adapter instance.
        """
        self._runner = runner

    def handle(self, command: RunImpactedTestsCommand) -> ImpactedTestsReport:
        """Identify impacted tests and execute pytest.

        Args:
            command: RunImpactedTestsCommand instance.

        Returns:
            ImpactedTestsReport domain model.
        """
        changed_lines = self._runner.get_changed_lines(
            command.repo_root, command.base_ref
        )
        changed_files = tuple(sorted(str(p) for p in changed_lines))

        if not changed_lines:
            return ImpactedTestsReport(
                changed_files=(),
                impacted_tests=(),
                dry_run=command.dry_run,
                exit_code=0,
            )

        impacted = self._runner.find_impacted_tests(
            changed_lines, command.coverage_file
        )
        impacted_tuple = tuple(sorted(impacted))

        if not impacted_tuple or command.dry_run:
            return ImpactedTestsReport(
                changed_files=changed_files,
                impacted_tests=impacted_tuple,
                dry_run=command.dry_run,
                exit_code=0,
            )

        exit_code = self._runner.execute_pytest(
            list(impacted_tuple),
            list(command.pytest_args),
            cwd=command.repo_root,
        )

        return ImpactedTestsReport(
            changed_files=changed_files,
            impacted_tests=impacted_tuple,
            dry_run=False,
            exit_code=exit_code,
        )
