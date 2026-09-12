"""Unit tests for governance infrastructure bootstrapping.

Notes/Architectural Intent:
    Verifies that create_governance_bus instantiates SynchronousCommandBus, registers
    all governance command handlers, and enables end-to-end command dispatching.
"""

from pathlib import Path
from unittest.mock import MagicMock, patch

from hexastack_tools.domain.analysis import (
    CodeQlScanReport,
    FuzzRunCommand,
    FuzzRunReport,
    InlineSnapshotsReport,
    ScanCodeQlCommand,
    UpdateInlineSnapshotsCommand,
)
from hexastack_tools.domain.dependencies import (
    AuditExtrasParityCommand,
    ExtrasAuditResult,
)
from hexastack_tools.domain.generators import (
    ArchonReport,
    GenerateArchonTestsCommand,
    GeneratePydepsCommand,
    GenerateUsageDocsCommand,
    PydepsReport,
    UsageDocsReport,
)
from hexastack_tools.domain.github import (
    ChecksReport,
    CodeScanningReport,
    ExaminePrCommand,
    ExaminePrReport,
    InspectChecksCommand,
    InspectCodeScanningCommand,
    InspectRepoCommand,
    InspectSecurityCommentsCommand,
    PrSummary,
    RepoStatus,
    SecurityCommentsReport,
)
from hexastack_tools.domain.governance import (
    CheckResult,
    CheckStatus,
    RunLinterCommand,
    RunSanityCheckCommand,
    SanityCheckReport,
    SanityTarget,
)
from hexastack_tools.domain.pypi import (
    BuildPackagesCommand,
    CheckPyPiReleasesCommand,
    PublishPackagesCommand,
    PyPiBuildReport,
    PyPiCheckReport,
    PyPiPublishReport,
    ReproducibleBuildReport,
    VerifyReproducibleBuildCommand,
)
from hexastack_tools.domain.refactoring import (
    AlphabetizeCodeCommand,
    AlphabetizeCodeReport,
    MediumPublishReport,
    PublishMediumArticlesCommand,
)
from hexastack_tools.domain.testing import (
    AuditTestBoundariesCommand,
    AuditTestRedundancyCommand,
    BoundaryAuditReport,
    ImpactedTestsReport,
    InspectMutationCacheCommand,
    MutationAuditReport,
    RedundancyAuditReport,
    RunImpactedTestsCommand,
    RunMutationTestsCommand,
)
from hexastack_tools.infra.bootstrap import create_governance_bus
from hexastack_tools.ports.dependencies import DependencyAuditorPort
from hexastack_tools.ports.github import GitHubApiPort
from hexastack_tools.ports.governance import ToolRunnerPort
from hexastack_tools.ports.pypi import PyPiClientPort
from hexastack_tools.ports.testing import TestingRunnerPort


def test_create_governance_bus_wires_and_dispatches():
    """Verify that create_governance_bus correctly wires commands to handlers."""
    mock_runner = MagicMock(spec=ToolRunnerPort)
    mock_runner.run_ruff.return_value = CheckResult(
        "Ruff", "test-pkg", CheckStatus.PASS, 0.05
    )
    mock_runner.run_ty.return_value = CheckResult(
        "Ty", "test-pkg", CheckStatus.PASS, 0.05
    )
    mock_runner.run_complexipy.return_value = CheckResult(
        "Complexity", "test-pkg", CheckStatus.PASS, 0.05
    )
    mock_runner.run_all_statements.return_value = CheckResult(
        "AllStatements", "test-pkg", CheckStatus.PASS, 0.05
    )
    mock_runner.run_test_parity.return_value = CheckResult(
        "Parity", "test-pkg", CheckStatus.PASS, 0.05
    )
    mock_runner.run_pytest.return_value = CheckResult(
        "Pytest", "test-pkg", CheckStatus.PASS, 0.05
    )

    mock_dep_auditor = MagicMock(spec=DependencyAuditorPort)
    mock_dep_auditor.audit_extras_parity.return_value = ExtrasAuditResult(
        violations=(),
        total_packages_checked=1,
    )

    mock_testing_runner = MagicMock(spec=TestingRunnerPort)
    mock_testing_runner.run_mutmut.return_value = 0
    mock_testing_runner.read_mutmut_cache.return_value = []
    mock_testing_runner.get_changed_lines.return_value = {}
    mock_testing_runner.find_impacted_tests.return_value = set()
    mock_testing_runner.get_tests_covering_line.return_value = []
    mock_testing_runner.audit_layer_boundary_leaks.return_value = []
    mock_testing_runner.audit_redundant_tests.return_value = []
    mock_testing_runner.execute_pytest.return_value = 0

    mock_github_client = MagicMock(spec=GitHubApiPort)
    mock_summary = PrSummary(
        number=1,
        title="Test PR",
        author="user",
        state="open",
        mergeable="mergeable",
        is_draft=False,
        head_ref="head",
        base_ref="base",
        html_url="url",
    )
    mock_github_client.get_pr_summary.return_value = mock_summary
    mock_github_client.get_check_runs.return_value = []
    mock_github_client.get_single_alert.return_value = MagicMock()
    mock_github_client.get_code_scanning_alerts.return_value = []
    mock_github_client.get_repo_status.return_value = MagicMock(spec=RepoStatus)

    mock_pypi_client = MagicMock(spec=PyPiClientPort)
    mock_pypi_client.check_version_exists.return_value = False
    mock_pypi_client.build_package.return_value = (True, "built")
    mock_pypi_client.publish_package.return_value = (True, "published")
    mock_pypi_client.get_git_commit_epoch.return_value = "1700000000"

    bus = create_governance_bus(
        runner=mock_runner,
        dependency_auditor=mock_dep_auditor,
        testing_runner=mock_testing_runner,
        github_client=mock_github_client,
        pypi_client=mock_pypi_client,
    )

    # 1. Test dispatching a single governance command
    linter_cmd = RunLinterCommand(paths=(Path(),), target_name="test-pkg")
    linter_res = bus.dispatch(linter_cmd)
    assert isinstance(linter_res, CheckResult)
    assert linter_res.check_name == "Ruff"

    # 2. Test dispatching composite sanity command
    target = SanityTarget(
        name="test-pkg",
        kind="package",
        path=Path("/tmp/pkg"),
        src_paths=(Path("/tmp/pkg/src"),),
        test_paths=(Path("/tmp/pkg/tests"),),
    )
    sanity_cmd = RunSanityCheckCommand(
        targets=(target,),
        repo_root=Path("/tmp"),
    )
    report = bus.dispatch(sanity_cmd)
    assert isinstance(report, SanityCheckReport)
    assert report.exit_code == 0
    assert len(report.results) == 6

    # 3. Test dispatching dependency command
    extras_cmd = AuditExtrasParityCommand(repo_root=Path("/tmp"))
    extras_res = bus.dispatch(extras_cmd)
    assert isinstance(extras_res, ExtrasAuditResult)
    assert extras_res.is_healthy is True

    # 4. Test dispatching testing commands
    mutmut_res = bus.dispatch(RunMutationTestsCommand())
    assert mutmut_res == 0

    inspect_res = bus.dispatch(InspectMutationCacheCommand(package="core"))
    assert isinstance(inspect_res, MutationAuditReport)

    boundary_res = bus.dispatch(AuditTestBoundariesCommand())
    assert isinstance(boundary_res, BoundaryAuditReport)

    redundancy_res = bus.dispatch(AuditTestRedundancyCommand())
    assert isinstance(redundancy_res, RedundancyAuditReport)

    impact_res = bus.dispatch(RunImpactedTestsCommand())
    assert isinstance(impact_res, ImpactedTestsReport)

    # 5. Test dispatching GitHub commands
    examine_res = bus.dispatch(ExaminePrCommand(pr_number=1))
    assert isinstance(examine_res, ExaminePrReport)

    checks_res = bus.dispatch(InspectChecksCommand(ref_or_pr="1"))
    assert isinstance(checks_res, ChecksReport)

    code_scan_res = bus.dispatch(InspectCodeScanningCommand(alert_number=1))
    assert isinstance(code_scan_res, CodeScanningReport)

    repo_res = bus.dispatch(InspectRepoCommand())
    assert isinstance(repo_res, RepoStatus)

    sec_res = bus.dispatch(InspectSecurityCommentsCommand(pr_number=1))
    assert isinstance(sec_res, SecurityCommentsReport)

    # 6. Test dispatching PyPI commands
    pypi_check_res = bus.dispatch(CheckPyPiReleasesCommand())
    assert isinstance(pypi_check_res, PyPiCheckReport)

    pypi_build_res = bus.dispatch(BuildPackagesCommand())
    assert isinstance(pypi_build_res, PyPiBuildReport)

    pypi_pub_res = bus.dispatch(PublishPackagesCommand())
    assert isinstance(pypi_pub_res, PyPiPublishReport)

    repro_res = bus.dispatch(VerifyReproducibleBuildCommand())
    assert isinstance(repro_res, ReproducibleBuildReport)

    # 7. Test dispatching Generator commands
    with (
        patch(
            "hexastack_tools.infra.handlers.generators.generate_overview_diagram",
            return_value="ov.svg",
        ),
        patch(
            "hexastack_tools.infra.handlers.generators.generate_package_diagram",
            return_value="pkg.svg",
        ),
        patch(
            "hexastack_tools.infra.handlers.generators.get_package_directories",
            return_value=[],
        ),
    ):
        pydeps_res = bus.dispatch(GeneratePydepsCommand())
        assert isinstance(pydeps_res, PydepsReport)

    with (
        patch("hexastack_tools.commands.usage_docs._TARGET_GENERATORS", {}),
        patch(
            "hexastack_tools.commands.usage_docs.resolve_impacted_usage_targets",
            return_value=[],
        ),
    ):
        usage_res = bus.dispatch(GenerateUsageDocsCommand(check_only=True))
        assert isinstance(usage_res, UsageDocsReport)

    with (
        patch(
            "hexastack_tools.infra.handlers.generators.get_package_directories",
            return_value=[],
        ),
    ):
        archon_res = bus.dispatch(GenerateArchonTestsCommand())
        assert isinstance(archon_res, ArchonReport)

    # 8. Test dispatching Analysis commands
    with (
        patch("shutil.which", return_value=None),
        patch("pathlib.Path.is_file", return_value=False),
    ):
        codeql_res = bus.dispatch(ScanCodeQlCommand())
        assert isinstance(codeql_res, CodeQlScanReport)

    with patch("hexastack_tools.commands.fuzz.run_target_fuzz", return_value=[]):
        fuzz_res = bus.dispatch(FuzzRunCommand())
        assert isinstance(fuzz_res, FuzzRunReport)

    with patch(
        "hexastack_tools.utils.workspace.get_package_directories", return_value=[]
    ):
        snap_res = bus.dispatch(UpdateInlineSnapshotsCommand())
        assert isinstance(snap_res, InlineSnapshotsReport)

    # 9. Test dispatching Refactoring commands
    alpha_res = bus.dispatch(
        AlphabetizeCodeCommand(targets=(Path("/tmp/nonexistent.py"),))
    )
    assert isinstance(alpha_res, AlphabetizeCodeReport)

    medium_res = bus.dispatch(PublishMediumArticlesCommand())
    assert isinstance(medium_res, MediumPublishReport)
