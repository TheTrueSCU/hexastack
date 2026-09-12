"""Unit tests for multi-format analysis presenters."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock

from rich.console import Console

from hexastack_tools.adapters.presenters.analysis import (
    JsonAnalysisPresenterAdapter,
    MarkdownAnalysisPresenterAdapter,
    RichAnalysisPresenterAdapter,
    create_analysis_presenter,
)
from hexastack_tools.domain.analysis import (
    CodeQlScanReport,
    FuzzRunReport,
    FuzzTargetResult,
    InlineSnapshotsReport,
)


def test_create_analysis_presenter_factory() -> None:
    """Verify create_analysis_presenter instantiates correct adapter."""
    assert isinstance(create_analysis_presenter("rich"), RichAnalysisPresenterAdapter)
    assert isinstance(create_analysis_presenter("table"), RichAnalysisPresenterAdapter)
    assert isinstance(create_analysis_presenter("json"), JsonAnalysisPresenterAdapter)
    assert isinstance(
        create_analysis_presenter("markdown"), MarkdownAnalysisPresenterAdapter
    )
    assert isinstance(create_analysis_presenter("md"), MarkdownAnalysisPresenterAdapter)


def test_rich_analysis_presenter() -> None:
    """Verify RichAnalysisPresenterAdapter renders reports."""
    mock_console = MagicMock(spec=Console)
    presenter = RichAnalysisPresenterAdapter(console=mock_console)

    codeql_ok = CodeQlScanReport(
        sarif_path=Path("results.sarif"),
        findings_count=0,
        is_successful=True,
    )
    assert presenter.present_codeql(codeql_ok) == 0

    codeql_err = CodeQlScanReport(
        error_message="failed to build db",
        is_successful=False,
    )
    assert presenter.present_codeql(codeql_err) == 1

    fuzz_res = FuzzTargetResult(
        target="sanitizer",
        engine="atheris",
        runs=100,
        duration_seconds=0.5,
        crashes=0,
        redos_violations=0,
        passed=True,
    )
    fuzz_ok = FuzzRunReport(results=(fuzz_res,), all_passed=True)
    assert presenter.present_fuzz(fuzz_ok) == 0

    fuzz_fail_res = FuzzTargetResult(
        target="owasp",
        engine="hypothesis",
        runs=100,
        duration_seconds=1.0,
        crashes=1,
        redos_violations=0,
        passed=False,
    )
    fuzz_err = FuzzRunReport(results=(fuzz_fail_res,), all_passed=False)
    assert presenter.present_fuzz(fuzz_err) == 1

    snap_rep = InlineSnapshotsReport(targets_updated=("packages/core",), exit_code=0)
    assert presenter.present_inline_snapshots(snap_rep) == 0


def test_json_analysis_presenter() -> None:
    """Verify JsonAnalysisPresenterAdapter formats output as JSON."""
    mock_console = MagicMock(spec=Console)
    presenter = JsonAnalysisPresenterAdapter(console=mock_console)

    codeql_ok = CodeQlScanReport(is_successful=True)
    assert presenter.present_codeql(codeql_ok) == 0
    mock_console.print_json.assert_called()

    fuzz_ok = FuzzRunReport(all_passed=True)
    assert presenter.present_fuzz(fuzz_ok) == 0

    snap_rep = InlineSnapshotsReport(exit_code=0)
    assert presenter.present_inline_snapshots(snap_rep) == 0


def test_markdown_analysis_presenter() -> None:
    """Verify MarkdownAnalysisPresenterAdapter formats output as Markdown."""
    mock_console = MagicMock(spec=Console)
    presenter = MarkdownAnalysisPresenterAdapter(console=mock_console)

    codeql_rep = CodeQlScanReport(
        sarif_path=Path("results.sarif"),
        findings_count=2,
        critical_count=1,
        is_successful=True,
    )
    assert presenter.present_codeql(codeql_rep) == 1  # critical > 0 returns 1

    fuzz_ok = FuzzRunReport(all_passed=True)
    assert presenter.present_fuzz(fuzz_ok) == 0

    snap_rep = InlineSnapshotsReport(exit_code=0)
    assert presenter.present_inline_snapshots(snap_rep) == 0
