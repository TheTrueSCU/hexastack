"""Unit tests for CQRS handlers.

Notes/Architectural Intent:
    Validates handler execution, port delegation, and event publishing.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from hexastack_qual.adapters.cqrs.commands import (
    FormatStatementsCommand,
    RunMutationTestingCommand,
    RunSanityCheckCommand,
    SyncAgentAssetsCommand,
)
from hexastack_qual.adapters.cqrs.handlers import (
    FormatStatementsHandler,
    GetPrHealthHandler,
    GetQualityScorecardHandler,
    GetTestImpactHandler,
    InspectMutantsHandler,
    RunMutationTestingHandler,
    RunSanityCheckHandler,
    SyncAgentAssetsHandler,
)
from hexastack_qual.adapters.cqrs.queries import (
    GetPrHealthQuery,
    GetQualityScorecardQuery,
    GetTestImpactQuery,
    InspectMutantsQuery,
)
from hexastack_qual.domain.models import (
    MutantReport,
    PrHealthSummary,
    QualityCheckResult,
    QualityScorecard,
)


@pytest.mark.asyncio
async def test_run_sanity_check_handler_healthy() -> None:
    """Ensure RunSanityCheckHandler executes and returns healthy scorecard."""
    auditor = MagicMock()
    auditor.run_sanity.return_value = QualityScorecard(target="core", is_healthy=True)
    event_bus = AsyncMock()

    handler = RunSanityCheckHandler(auditor=auditor, event_bus=event_bus)
    cmd = RunSanityCheckCommand(package="core", skip_tests=True)
    res = await handler(cmd)

    healthy = res.is_healthy
    assert healthy is True
    call_count = event_bus.publish.call_count
    assert call_count == 0


@pytest.mark.asyncio
async def test_run_sanity_check_handler_unhealthy_emits_event() -> None:
    """Ensure RunSanityCheckHandler publishes event on failure with exact failed checks."""
    check_fail = QualityCheckResult(
        check_name="Ruff",
        target="core",
        status="fail",
        duration_seconds=0.1,
    )
    check_pass = QualityCheckResult(
        check_name="Ty",
        target="core",
        status="pass",
        duration_seconds=0.1,
    )
    auditor = MagicMock()
    auditor.run_sanity.return_value = QualityScorecard(
        target="core",
        is_healthy=False,
        checks=[check_fail, check_pass],
    )
    event_bus = AsyncMock()

    handler = RunSanityCheckHandler(auditor=auditor, event_bus=event_bus)
    cmd = RunSanityCheckCommand(package="core")
    res = await handler(cmd)

    healthy = res.is_healthy
    assert healthy is False
    call_count = event_bus.publish.call_count
    assert call_count == 1
    event = event_bus.publish.call_args[0][0]
    target = event.target
    assert target == "core"
    failed_checks = event.failed_checks
    assert failed_checks == ["Ruff"]


@pytest.mark.asyncio
async def test_format_statements_handler() -> None:
    """Ensure FormatStatementsHandler fixes statements and emits event if modified."""
    auditor = MagicMock()
    auditor.fix_statements.return_value = 1
    event_bus = AsyncMock()

    handler = FormatStatementsHandler(auditor=auditor, event_bus=event_bus)
    cmd = FormatStatementsCommand(package="events")
    count = await handler(cmd)

    assert count == 1
    call_count = event_bus.publish.call_count
    assert call_count == 1
    event = event_bus.publish.call_args[0][0]
    target = event.target
    assert target == "events"
    modified = event.files_modified
    assert modified == 1


@pytest.mark.asyncio
async def test_format_statements_handler_workspace_target() -> None:
    """Ensure FormatStatementsHandler defaults to workspace target when package is None."""
    auditor = MagicMock()
    auditor.fix_statements.return_value = 5
    event_bus = AsyncMock()

    handler = FormatStatementsHandler(auditor=auditor, event_bus=event_bus)
    cmd = FormatStatementsCommand(package=None)
    count = await handler(cmd)

    assert count == 5
    call_count = event_bus.publish.call_count
    assert call_count == 1
    event = event_bus.publish.call_args[0][0]
    target = event.target
    assert target == "workspace"
    modified = event.files_modified
    assert modified == 5


@pytest.mark.asyncio
async def test_format_statements_handler_no_modification_no_event() -> None:
    """Ensure FormatStatementsHandler does not emit event when 0 files were modified."""
    auditor = MagicMock()
    auditor.fix_statements.return_value = 0
    event_bus = AsyncMock()

    handler = FormatStatementsHandler(auditor=auditor, event_bus=event_bus)
    cmd = FormatStatementsCommand(package="events")
    count = await handler(cmd)

    assert count == 0
    call_count = event_bus.publish.call_count
    assert call_count == 0


@pytest.mark.asyncio
async def test_run_mutation_testing_handler() -> None:
    """Ensure RunMutationTestingHandler delegates to mutator."""
    mutator = MagicMock()
    mutator.run_mutation_testing.return_value = MutantReport(
        package_name="db",
        mutation_score=95.0,
    )

    handler = RunMutationTestingHandler(mutator=mutator)
    cmd = RunMutationTestingCommand(package="db", reset=True)
    report = await handler(cmd)

    assert report.package_name == "db"
    assert report.mutation_score == 95.0


@pytest.mark.asyncio
async def test_sync_agent_assets_handler() -> None:
    """Ensure SyncAgentAssetsHandler delegates to sync_managed_assets."""
    mock_res = MagicMock()
    mock_res.created_count = 2
    mock_res.updated_count = 1

    handler = SyncAgentAssetsHandler()
    with patch(
        "hexastack_qual.adapters.cqrs.handlers.FileSystemAgentAssetAdapter.sync_assets",
        return_value=mock_res,
    ):
        cmd = SyncAgentAssetsCommand(dry_run=False)
        total = await handler(cmd)
        assert total == 3


@pytest.mark.asyncio
async def test_get_quality_scorecard_handler() -> None:
    """Ensure GetQualityScorecardHandler returns scorecard."""
    auditor = MagicMock()
    auditor.run_sanity.return_value = QualityScorecard(target="ai", is_healthy=True)

    handler = GetQualityScorecardHandler(auditor=auditor)
    query = GetQualityScorecardQuery(package="ai")
    scorecard = await handler(query)

    assert scorecard.target == "ai"
    assert scorecard.is_healthy is True


@pytest.mark.asyncio
async def test_inspect_mutants_handler() -> None:
    """Ensure InspectMutantsHandler returns mutant report."""
    mutator = MagicMock()
    mutator.inspect_surviving_mutants.return_value = MutantReport(
        package_name="grpc",
        mutation_score=88.0,
    )

    handler = InspectMutantsHandler(mutator=mutator)
    query = InspectMutantsQuery(package="grpc")
    report = await handler(query)

    assert report.package_name == "grpc"
    assert report.mutation_score == 88.0


@pytest.mark.asyncio
async def test_get_test_impact_handler() -> None:
    """Ensure GetTestImpactHandler returns impacted packages."""
    diagnostics = MagicMock()
    diagnostics.get_test_impact.return_value = ["core", "events"]

    handler = GetTestImpactHandler(diagnostics=diagnostics)
    query = GetTestImpactQuery(base_ref="origin/main")
    impact = await handler(query)

    assert impact == ["core", "events"]


@pytest.mark.asyncio
async def test_get_pr_health_handler() -> None:
    """Ensure GetPrHealthHandler returns PR health summary."""
    diagnostics = MagicMock()
    diagnostics.get_pr_health.return_value = PrHealthSummary(
        pr_number=77,
        title="fix: resolve race",
        state="open",
        ci_status="success",
    )

    handler = GetPrHealthHandler(diagnostics=diagnostics)
    query = GetPrHealthQuery(pr_number=77)
    health = await handler(query)

    assert health.pr_number == 77
    assert health.ci_status == "success"
