"""CQRS command and query handlers for hexastack-qual.

Notes/Architectural Intent:
    Connects CQRS message dispatching to QualityAuditorPort, MutationInspectorPort,
    and PrDiagnosticPort, with optional event emission across EventBusPort.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from hexaqual.adapters.agents import FileSystemAgentAssetAdapter
from hexaqual.adapters.workspace import get_repo_root

from hexastack_qual.adapters.cqrs.commands import (
    FormatStatementsCommand,
    RunMutationTestingCommand,
    RunSanityCheckCommand,
    SyncAgentAssetsCommand,
)
from hexastack_qual.adapters.cqrs.queries import (
    GetPrHealthQuery,
    GetQualityScorecardQuery,
    GetTestImpactQuery,
    InspectMutantsQuery,
)
from hexastack_qual.domain.events import (
    QualityGateFailedEvent,
    StatementsFixedEvent,
)
from hexastack_qual.domain.models import (
    MutantReport,
    PrHealthSummary,
    QualityScorecard,
)

if TYPE_CHECKING:
    from hexastack_cqrs.ports.buses import EventBusPort
    from hexastack_qual.ports.auditor import QualityAuditorPort
    from hexastack_qual.ports.diagnostics import PrDiagnosticPort
    from hexastack_qual.ports.mutator import MutationInspectorPort


class RunSanityCheckHandler:
    """Handler for RunSanityCheckCommand."""

    def __init__(
        self,
        auditor: QualityAuditorPort,
        event_bus: EventBusPort | None = None,
    ) -> None:
        """Initialize handler with auditor port and optional event bus."""
        self._auditor = auditor
        self._event_bus = event_bus

    async def __call__(self, command: RunSanityCheckCommand) -> QualityScorecard:
        """Execute sanity check and emit failure event if unhealthy."""
        scorecard = self._auditor.run_sanity(
            package=command.package,
            skip_tests=command.skip_tests,
        )
        if not scorecard.is_healthy and self._event_bus:
            failed_names = [
                c.check_name for c in scorecard.checks if c.status == "fail"
            ]
            event = QualityGateFailedEvent(
                target=scorecard.target,
                failed_checks=failed_names,
            )
            await self._event_bus.publish(event)
        return scorecard


class FormatStatementsHandler:
    """Handler for FormatStatementsCommand."""

    def __init__(
        self,
        auditor: QualityAuditorPort,
        event_bus: EventBusPort | None = None,
    ) -> None:
        """Initialize handler with auditor port and optional event bus."""
        self._auditor = auditor
        self._event_bus = event_bus

    async def __call__(self, command: FormatStatementsCommand) -> int:
        """Fix statement formatting and emit event if files modified."""
        modified_count = self._auditor.fix_statements(package=command.package)
        if modified_count > 0 and self._event_bus:
            event = StatementsFixedEvent(
                target=command.package or "workspace",
                files_modified=modified_count,
            )
            await self._event_bus.publish(event)
        return modified_count


class RunMutationTestingHandler:
    """Handler for RunMutationTestingCommand."""

    def __init__(self, mutator: MutationInspectorPort) -> None:
        """Initialize handler with mutation inspector port."""
        self._mutator = mutator

    async def __call__(self, command: RunMutationTestingCommand) -> MutantReport:
        """Execute mutation testing runner."""
        return self._mutator.run_mutation_testing(
            package=command.package,
            reset=command.reset,
        )


class SyncAgentAssetsHandler:
    """Handler for SyncAgentAssetsCommand."""

    async def __call__(self, command: SyncAgentAssetsCommand) -> int:
        """Synchronize universal AI agent rules and workflows."""
        root = get_repo_root()
        adapter = FileSystemAgentAssetAdapter()
        res = adapter.sync_assets(root, dry_run=command.dry_run)
        return res.created_count + res.updated_count


class GetQualityScorecardHandler:
    """Handler for GetQualityScorecardQuery."""

    def __init__(self, auditor: QualityAuditorPort) -> None:
        """Initialize handler with auditor port."""
        self._auditor = auditor

    async def __call__(self, query: GetQualityScorecardQuery) -> QualityScorecard:
        """Execute sanity check and return scorecard."""
        return self._auditor.run_sanity(
            package=query.package,
            skip_tests=query.skip_tests,
        )


class InspectMutantsHandler:
    """Handler for InspectMutantsQuery."""

    def __init__(self, mutator: MutationInspectorPort) -> None:
        """Initialize handler with mutator port."""
        self._mutator = mutator

    async def __call__(self, query: InspectMutantsQuery) -> MutantReport:
        """Inspect surviving mutants."""
        return self._mutator.inspect_surviving_mutants(
            package=query.package,
            actionable_only=query.actionable_only,
        )


class GetTestImpactHandler:
    """Handler for GetTestImpactQuery."""

    def __init__(self, diagnostics: PrDiagnosticPort) -> None:
        """Initialize handler with diagnostics port."""
        self._diagnostics = diagnostics

    async def __call__(self, query: GetTestImpactQuery) -> list[str]:
        """Compute impacted test suites."""
        return self._diagnostics.get_test_impact(base_ref=query.base_ref)


class GetPrHealthHandler:
    """Handler for GetPrHealthQuery."""

    def __init__(self, diagnostics: PrDiagnosticPort) -> None:
        """Initialize handler with diagnostics port."""
        self._diagnostics = diagnostics

    async def __call__(self, query: GetPrHealthQuery) -> PrHealthSummary:
        """Inspect pull request diagnostic health."""
        return self._diagnostics.get_pr_health(pr_number=query.pr_number)


__all__ = [
    "FormatStatementsHandler",
    "GetPrHealthHandler",
    "GetQualityScorecardHandler",
    "GetTestImpactHandler",
    "InspectMutantsHandler",
    "RunMutationTestingHandler",
    "RunSanityCheckHandler",
    "SyncAgentAssetsHandler",
]
