"""Unit tests for governance domain models and commands.

Notes/Architectural Intent:
    Verifies that governance commands, enums, targets, and result aggregates
    instantiate correctly with immutable data invariants.
"""

from pathlib import Path

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


def test_check_status_enum():
    """Verify CheckStatus enum members."""
    assert CheckStatus.PASS.value == "PASS"
    assert CheckStatus.FAIL.value == "FAIL"
    assert CheckStatus.SKIP.value == "SKIP"


def test_sanity_target_and_check_result():
    """Verify SanityTarget and CheckResult creation."""
    target = SanityTarget(
        name="test-pkg",
        kind="package",
        path=Path("/tmp/test"),
        src_paths=(Path("/tmp/test/src"),),
        test_paths=(Path("/tmp/test/tests"),),
    )
    assert target.name == "test-pkg"
    assert target.kind == "package"

    result = CheckResult(
        check_name="Ruff",
        target_name="test-pkg",
        status=CheckStatus.PASS,
        duration=0.12,
        details="Clean",
    )
    assert result.status == CheckStatus.PASS
    assert result.duration == 0.12

    report = SanityCheckReport(
        results=(result,),
        total_duration=0.12,
        exit_code=0,
    )
    assert report.exit_code == 0
    assert len(report.results) == 1


def test_governance_commands():
    """Verify instantiation of all governance command objects."""
    target = SanityTarget(
        name="cqrs",
        kind="package",
        path=Path("/tmp/cqrs"),
        src_paths=(Path("/tmp/cqrs/src"),),
        test_paths=(Path("/tmp/cqrs/tests"),),
    )
    repo_root = Path("/tmp/repo")

    cmd_lint = RunLinterCommand(paths=target.src_paths, target_name="cqrs", fix=True)
    assert cmd_lint.fix is True

    cmd_ty = RunTypecheckCommand(paths=target.src_paths, target_name="cqrs")
    assert cmd_ty.target_name == "cqrs"

    cmd_cpx = AuditComplexityCommand(
        paths=target.src_paths, target_name="cqrs", max_complexity=20
    )
    assert cmd_cpx.max_complexity == 20

    cmd_all = CheckAllStatementsCommand(paths=target.src_paths, target_name="cqrs")
    assert cmd_all.fix is False

    cmd_parity = CheckTestParityCommand(target=target, repo_root=repo_root)
    assert cmd_parity.target.name == "cqrs"

    cmd_test = RunPytestCommand(target=target, repo_root=repo_root, skip=True)
    assert cmd_test.skip is True

    cmd_sanity = RunSanityCheckCommand(
        targets=(target,),
        repo_root=repo_root,
        fix=False,
        skip_tests=False,
        max_complexity=25,
    )
    assert len(cmd_sanity.targets) == 1
