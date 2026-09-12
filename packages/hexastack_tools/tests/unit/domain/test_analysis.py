"""Unit tests for domain analysis models and CQRS commands."""

from __future__ import annotations

from pathlib import Path

from hexastack_tools.domain.analysis import (
    CodeQlScanReport,
    FuzzRunCommand,
    FuzzRunReport,
    FuzzTargetResult,
    InlineSnapshotsReport,
    ScanCodeQlCommand,
    UpdateInlineSnapshotsCommand,
)


def test_codeql_domain_models() -> None:
    """Verify CodeQlScanReport and ScanCodeQlCommand."""
    rep = CodeQlScanReport(
        sarif_path=Path("results.sarif"),
        findings_count=3,
        critical_count=1,
        is_successful=True,
    )
    assert rep.findings_count == 3
    assert rep.critical_count == 1
    assert rep.is_successful is True

    cmd = ScanCodeQlCommand(query_suite="custom-pack", threads=4)
    assert cmd.query_suite == "custom-pack"
    assert cmd.threads == 4


def test_fuzz_domain_models() -> None:
    """Verify FuzzTargetResult, FuzzRunReport, and FuzzRunCommand."""
    target_res = FuzzTargetResult(
        target="sanitizer",
        engine="atheris",
        runs=500,
        duration_seconds=1.2,
        crashes=0,
        redos_violations=0,
        passed=True,
    )
    rep = FuzzRunReport(results=(target_res,), all_passed=True)
    assert len(rep.results) == 1
    assert rep.all_passed is True

    cmd = FuzzRunCommand(target="sanitizer", runs=500)
    assert cmd.target == "sanitizer"
    assert cmd.runs == 500


def test_inline_snapshot_domain_models() -> None:
    """Verify InlineSnapshotsReport and UpdateInlineSnapshotsCommand."""
    rep = InlineSnapshotsReport(targets_updated=("packages/core",), exit_code=0)
    assert rep.exit_code == 0
    assert len(rep.targets_updated) == 1

    cmd = UpdateInlineSnapshotsCommand(mode="review", targets=(Path("packages/core"),))
    assert cmd.mode == "review"
    assert len(cmd.targets) == 1
