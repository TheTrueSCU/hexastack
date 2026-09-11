"""Bootstrap wiring and dependency registration for Hexastack Tools.

Notes/Architectural Intent:
    Assembles the SynchronousCommandBus, binds domain Command types to their
    respective CommandHandler implementations, and injects the ToolRunnerPort adapter.
"""

from __future__ import annotations

from typing import Any

from hexastack_cqrs.adapters.buses.command.synchronous import SynchronousCommandBus
from hexastack_cqrs.infra.registries import HandlerRegistry
from hexastack_tools.adapters.github import GitHubHttpAdapter
from hexastack_tools.adapters.runners.dependency_runner import (
    SubprocessDependencyAuditorAdapter,
)
from hexastack_tools.adapters.runners.pypi_runner import (
    SubprocessPyPiRunnerAdapter,
)
from hexastack_tools.adapters.runners.subprocess_runner import (
    SubprocessToolRunnerAdapter,
)
from hexastack_tools.adapters.runners.testing_runner import (
    SubprocessTestingRunnerAdapter,
)
from hexastack_tools.domain.dependencies import (
    AuditExtrasParityCommand,
    GenerateImportLinterConfigCommand,
    RunDeptryAuditCommand,
    RunImportLinterCommand,
    RunUnifiedDepsAuditCommand,
)
from hexastack_tools.domain.github import (
    CheckRunFinding,
    ExaminePrCommand,
    InspectChecksCommand,
    InspectCodeScanningCommand,
    InspectRepoCommand,
    InspectSecurityCommentsCommand,
    PrSummary,
    RepoStatus,
    ReviewThread,
    SecurityAlert,
)
from hexastack_tools.domain.governance import (
    AuditComplexityCommand,
    CheckAllStatementsCommand,
    CheckTestParityCommand,
    RunLinterCommand,
    RunPytestCommand,
    RunSanityCheckCommand,
    RunTypecheckCommand,
)
from hexastack_tools.domain.pypi import (
    BuildPackagesCommand,
    CheckPyPiReleasesCommand,
    PublishPackagesCommand,
    VerifyReproducibleBuildCommand,
)
from hexastack_tools.domain.testing import (
    AuditTestBoundariesCommand,
    AuditTestRedundancyCommand,
    InspectMutationCacheCommand,
    RunImpactedTestsCommand,
    RunMutationTestsCommand,
)
from hexastack_tools.infra.handlers.dependencies import (
    AuditExtrasParityHandler,
    GenerateImportLinterConfigHandler,
    RunDeptryAuditHandler,
    RunImportLinterHandler,
    RunUnifiedDepsAuditHandler,
)
from hexastack_tools.infra.handlers.github import (
    ExaminePrHandler,
    InspectChecksHandler,
    InspectCodeScanningHandler,
    InspectRepoHandler,
    InspectSecurityCommentsHandler,
)
from hexastack_tools.infra.handlers.governance import (
    AuditComplexityHandler,
    CheckAllStatementsHandler,
    CheckTestParityHandler,
    RunLinterHandler,
    RunPytestHandler,
    RunSanityCheckHandler,
    RunTypecheckHandler,
)
from hexastack_tools.infra.handlers.pypi import (
    BuildPackagesHandler,
    CheckPyPiReleasesHandler,
    PublishPackagesHandler,
    VerifyReproducibleBuildHandler,
)
from hexastack_tools.infra.handlers.testing import (
    AuditTestBoundariesHandler,
    AuditTestRedundancyHandler,
    InspectMutationCacheHandler,
    RunImpactedTestsHandler,
    RunMutationTestsHandler,
)
from hexastack_tools.ports.dependencies import DependencyAuditorPort
from hexastack_tools.ports.github import GitHubApiPort
from hexastack_tools.ports.governance import ToolRunnerPort
from hexastack_tools.ports.pypi import PyPiClientPort
from hexastack_tools.ports.testing import TestingRunnerPort

__all__ = [
    "create_governance_bus",
]


class _LazyGitHubClient(GitHubApiPort):
    """Lazy proxy initializing GitHubHttpAdapter only upon first method invocation."""

    def __init__(self) -> None:
        self._client: GitHubApiPort | None = None

    def _get_client(self) -> GitHubApiPort:
        if self._client is None:
            self._client = GitHubHttpAdapter()
        return self._client

    def get_repo_status(
        self, owner: str | None = None, repo: str | None = None
    ) -> RepoStatus:
        return self._get_client().get_repo_status(owner=owner, repo=repo)

    def get_pr_summary(self, pr_number: int) -> PrSummary:
        return self._get_client().get_pr_summary(pr_number)

    def get_check_runs(self, ref: str) -> list[CheckRunFinding]:
        return self._get_client().get_check_runs(ref)

    def get_review_threads(self, pr_number: int) -> list[ReviewThread]:
        return self._get_client().get_review_threads(pr_number)

    def get_code_scanning_alerts(
        self, ref: str | None = None, state: str = "open"
    ) -> list[SecurityAlert]:
        return self._get_client().get_code_scanning_alerts(ref=ref, state=state)

    def get_single_alert(self, alert_number: int) -> SecurityAlert:
        return self._get_client().get_single_alert(alert_number)

    def get_failed_run_logs(self, run_id: int | str) -> str | None:
        return self._get_client().get_failed_run_logs(run_id)

    def get_workflow_runs(
        self, branch: str | None = None, limit: int = 5
    ) -> list[dict[str, Any]]:
        return self._get_client().get_workflow_runs(branch=branch, limit=limit)


def create_governance_bus(
    runner: ToolRunnerPort | None = None,
    dependency_auditor: DependencyAuditorPort | None = None,
    testing_runner: TestingRunnerPort | None = None,
    github_client: GitHubApiPort | None = None,
    pypi_client: PyPiClientPort | None = None,
) -> SynchronousCommandBus:
    """Construct and configure CommandBus with all governance handlers registered.

    Args:
        runner: Optional ToolRunnerPort adapter. Defaults to SubprocessToolRunnerAdapter.
        dependency_auditor: Optional DependencyAuditorPort adapter. Defaults to
            SubprocessDependencyAuditorAdapter.
        testing_runner: Optional TestingRunnerPort adapter. Defaults to
            SubprocessTestingRunnerAdapter.
        github_client: Optional GitHubApiPort adapter. Defaults to GitHubHttpAdapter.
        pypi_client: Optional PyPiClientPort adapter. Defaults to SubprocessPyPiRunnerAdapter.

    Returns:
        Configured SynchronousCommandBus instance.

    Notes/Architectural Intent:
        Creates a circular binding where the composite RunSanityCheckHandler receives
        the bus itself to dispatch individual check commands, and registers
        governance, dependency audit, testing/mutation, GitHub, and PyPI handlers.
    """
    actual_runner = runner or SubprocessToolRunnerAdapter()
    actual_dep_auditor = dependency_auditor or SubprocessDependencyAuditorAdapter()
    actual_testing_runner = testing_runner or SubprocessTestingRunnerAdapter()
    actual_github_client = github_client or _LazyGitHubClient()
    actual_pypi_client = pypi_client or SubprocessPyPiRunnerAdapter()
    registry = HandlerRegistry()
    bus = SynchronousCommandBus(handler_registry=registry)

    # 1. Register leaf check handlers
    linter_handler = RunLinterHandler(actual_runner)
    registry.register(RunLinterCommand, linter_handler.handle)

    typecheck_handler = RunTypecheckHandler(actual_runner)
    registry.register(RunTypecheckCommand, typecheck_handler.handle)

    complexity_handler = AuditComplexityHandler(actual_runner)
    registry.register(AuditComplexityCommand, complexity_handler.handle)

    all_statements_handler = CheckAllStatementsHandler(actual_runner)
    registry.register(CheckAllStatementsCommand, all_statements_handler.handle)

    parity_handler = CheckTestParityHandler(actual_runner)
    registry.register(CheckTestParityCommand, parity_handler.handle)

    pytest_handler = RunPytestHandler(actual_runner)
    registry.register(RunPytestCommand, pytest_handler.handle)

    # 2. Register composite sanity check handler
    sanity_handler = RunSanityCheckHandler(bus)
    registry.register(RunSanityCheckCommand, sanity_handler.handle)

    # 3. Register dependency and boundary handlers
    extras_handler = AuditExtrasParityHandler(actual_dep_auditor)
    registry.register(AuditExtrasParityCommand, extras_handler.handle)

    deptry_handler = RunDeptryAuditHandler(actual_dep_auditor)
    registry.register(RunDeptryAuditCommand, deptry_handler.handle)

    import_linter_handler = RunImportLinterHandler(actual_dep_auditor)
    registry.register(RunImportLinterCommand, import_linter_handler.handle)

    generate_linter_handler = GenerateImportLinterConfigHandler(actual_dep_auditor)
    registry.register(GenerateImportLinterConfigCommand, generate_linter_handler.handle)

    unified_deps_handler = RunUnifiedDepsAuditHandler(actual_dep_auditor)
    registry.register(RunUnifiedDepsAuditCommand, unified_deps_handler.handle)

    # 4. Register testing and mutation handlers
    run_mutation_handler = RunMutationTestsHandler(actual_testing_runner)
    registry.register(RunMutationTestsCommand, run_mutation_handler.handle)

    inspect_mutation_handler = InspectMutationCacheHandler(actual_testing_runner)
    registry.register(InspectMutationCacheCommand, inspect_mutation_handler.handle)

    boundary_handler = AuditTestBoundariesHandler(actual_testing_runner)
    registry.register(AuditTestBoundariesCommand, boundary_handler.handle)

    redundancy_handler = AuditTestRedundancyHandler(actual_testing_runner)
    registry.register(AuditTestRedundancyCommand, redundancy_handler.handle)

    impact_handler = RunImpactedTestsHandler(actual_testing_runner)
    registry.register(RunImpactedTestsCommand, impact_handler.handle)

    # 5. Register GitHub inspection handlers
    examine_pr_handler = ExaminePrHandler(actual_github_client)
    registry.register(ExaminePrCommand, examine_pr_handler.handle)

    inspect_checks_handler = InspectChecksHandler(actual_github_client)
    registry.register(InspectChecksCommand, inspect_checks_handler.handle)

    inspect_code_scanning_handler = InspectCodeScanningHandler(actual_github_client)
    registry.register(InspectCodeScanningCommand, inspect_code_scanning_handler.handle)

    inspect_repo_handler = InspectRepoHandler(actual_github_client)
    registry.register(InspectRepoCommand, inspect_repo_handler.handle)

    inspect_security_comments_handler = InspectSecurityCommentsHandler(
        actual_github_client
    )
    registry.register(
        InspectSecurityCommentsCommand, inspect_security_comments_handler.handle
    )

    # 6. Register PyPI release handlers
    check_pypi_handler = CheckPyPiReleasesHandler(actual_pypi_client)
    registry.register(CheckPyPiReleasesCommand, check_pypi_handler.handle)

    build_pypi_handler = BuildPackagesHandler(actual_pypi_client)
    registry.register(BuildPackagesCommand, build_pypi_handler.handle)

    publish_pypi_handler = PublishPackagesHandler(actual_pypi_client)
    registry.register(PublishPackagesCommand, publish_pypi_handler.handle)

    verify_repro_handler = VerifyReproducibleBuildHandler(actual_pypi_client)
    registry.register(VerifyReproducibleBuildCommand, verify_repro_handler.handle)

    return bus
