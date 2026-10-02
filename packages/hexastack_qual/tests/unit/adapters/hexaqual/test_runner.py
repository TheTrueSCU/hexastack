"""Unit tests for HexaqualRunnerAdapter.

Notes/Architectural Intent:
    Validates that HexaqualRunnerAdapter interacts with workspace files,
    complexipy, and code analysis helpers, returning expected domain models.
"""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

from hexastack_qual.adapters.hexaqual.runner import HexaqualRunnerAdapter


def test_hexaqual_runner_adapter_init(tmp_path: Path) -> None:
    """Ensure adapter initializes with explicit or discovered repo root."""
    adapter = HexaqualRunnerAdapter(repo_root=tmp_path)
    assert adapter._repo_root == tmp_path


def test_audit_complexity(tmp_path: Path) -> None:
    """Ensure audit_complexity computes function scores and filters violations."""
    pkg_dir = tmp_path / "packages" / "foo" / "src" / "foo"
    pkg_dir.mkdir(parents=True)
    sample_file = pkg_dir / "service.py"
    sample_file.write_text("def simple(): return 1\n")

    adapter = HexaqualRunnerAdapter(repo_root=tmp_path)
    metrics = adapter.audit_complexity(package="foo", max_complexity=25)
    assert len(metrics) == 0


def test_audit_statements(tmp_path: Path) -> None:
    """Ensure audit_statements flags invalid __all__ files."""
    pkg_dir = tmp_path / "packages" / "foo" / "src" / "foo"
    pkg_dir.mkdir(parents=True)
    init_file = pkg_dir / "__init__.py"
    init_file.write_text('__all__ = ["z", "a"]\n')

    adapter = HexaqualRunnerAdapter(repo_root=tmp_path)
    findings = adapter.audit_statements(package="foo")
    assert len(findings) == 1
    assert findings[0].is_sorted is False


def test_fix_statements(tmp_path: Path) -> None:
    """Ensure fix_statements sorts unsorted __all__ and reports count."""
    pkg_dir = tmp_path / "packages" / "foo" / "src" / "foo"
    pkg_dir.mkdir(parents=True)
    init_file = pkg_dir / "__init__.py"
    init_file.write_text('__all__ = ["z", "a"]\n')

    adapter = HexaqualRunnerAdapter(repo_root=tmp_path)
    modified = adapter.fix_statements(package="foo")
    assert modified == 1


def test_run_sanity(tmp_path: Path) -> None:
    """Ensure run_sanity compiles checks into QualityScorecard."""
    adapter = HexaqualRunnerAdapter(repo_root=tmp_path)
    scorecard = adapter.run_sanity(package=None, skip_tests=True)
    assert len(scorecard.checks) == 3
    assert scorecard.is_healthy is True


def test_inspect_and_run_mutation_testing(tmp_path: Path) -> None:
    """Ensure mutation testing returns MutantReport."""
    adapter = HexaqualRunnerAdapter(repo_root=tmp_path)
    report = adapter.inspect_surviving_mutants("core")
    assert report.package_name == "core"
    assert report.mutation_score == 100.0

    run_report = adapter.run_mutation_testing("core", reset=True)
    assert run_report.package_name == "core"


def test_get_pr_health_with_mocked_subprocess(tmp_path: Path) -> None:
    """Ensure get_pr_health parses gh pr view json output."""
    adapter = HexaqualRunnerAdapter(repo_root=tmp_path)

    mock_proc = MagicMock()
    mock_proc.returncode = 0
    mock_proc.stdout = json.dumps(
        {
            "title": "feat: test pr",
            "state": "OPEN",
            "statusCheckRollup": [
                {"name": "CI", "conclusion": "SUCCESS"},
                {"name": "Lint", "conclusion": "FAILURE"},
            ],
        }
    )

    with (
        patch("shutil.which", return_value="/usr/bin/gh"),
        patch("subprocess.run", return_value=mock_proc),
    ):
        health = adapter.get_pr_health(101)
        assert health.pr_number == 101
        assert health.title == "feat: test pr"
        assert health.ci_status == "failure"
        assert health.total_checks == 2
        assert "Lint" in health.failed_checks


def test_get_test_impact(tmp_path: Path) -> None:
    """Ensure get_test_impact delegates to affected package resolver."""
    adapter = HexaqualRunnerAdapter(repo_root=tmp_path)
    with patch(
        "hexastack_qual.adapters.hexaqual.runner.resolve_affected_packages",
        return_value={"core", "cqrs"},
    ):
        impact = adapter.get_test_impact("origin/main")
        assert impact == ["core", "cqrs"]


def test_audit_openssf_returns_summary(tmp_path: Path) -> None:
    """Ensure audit_openssf delegates to hexaqual infra and returns OpenSsfAuditSummary."""
    from hexaqual.domain.openssf import CriterionProposal, CriterionStatus, OpenSsfTier
    from hexastack_qual.domain.models import OpenSsfAuditSummary

    adapter = HexaqualRunnerAdapter(repo_root=tmp_path)

    mock_proposal = CriterionProposal(
        criterion_id="dco",
        status=CriterionStatus.UNMET,
        justification="No DCO enforcement found",
        tier=OpenSsfTier.PASSING,
    )

    mock_posture = MagicMock()
    mock_posture.percentage = 75
    mock_posture.met_count = 3
    mock_posture.total_count = 4
    mock_posture.proposals = [mock_proposal]

    with (
        patch(
            "hexastack_qual.adapters.hexaqual.runner.resolve_local_repo_url",
            return_value="https://github.com/test/repo",
        ),
        patch(
            "hexastack_qual.adapters.hexaqual.runner.evaluate_local_heuristics",
            return_value=[mock_proposal],
        ),
        patch(
            "hexastack_qual.adapters.hexaqual.runner.audit_project_posture",
            return_value=mock_posture,
        ),
    ):
        result = adapter.audit_openssf()

    assert isinstance(result, OpenSsfAuditSummary)
    assert result.project_url == "https://github.com/test/repo"
    assert result.passing_score == 75.0
    assert result.met_count == 3
    assert len(result.unmet_criteria) >= 1
    assert result.unmet_criteria[0].criterion_id == "dco"


def test_check_openssf_compliance_returns_result(tmp_path: Path) -> None:
    """Ensure check_openssf_compliance delegates to hexaqual and returns OpenSsfComplianceResult."""
    from hexaqual.domain.openssf import OpenSsfCheckResult, OpenSsfTier
    from hexastack_qual.domain.models import OpenSsfComplianceResult

    adapter = HexaqualRunnerAdapter(repo_root=tmp_path)

    mock_result = OpenSsfCheckResult(
        passed=False,
        tier=OpenSsfTier.PASSING,
        badge_level="",
        score=80,
        min_score=100,
        unmet_must=[{"criterion_id": "dco"}, {"criterion_id": "sha-pinning"}],
        errors=[],
    )

    with (
        patch(
            "hexastack_qual.adapters.hexaqual.runner.evaluate_local_heuristics",
            return_value=[],
        ),
        patch(
            "hexastack_qual.adapters.hexaqual.runner.verify_openssf_compliance",
            return_value=mock_result,
        ),
    ):
        result = adapter.check_openssf_compliance(tier="passing", min_score=100.0)

    assert isinstance(result, OpenSsfComplianceResult)
    assert result.is_compliant is False
    assert result.required_tier == "passing"
    assert result.required_score == 100.0
    assert "dco" in result.failure_reasons


def test_generate_openssf_checklist_returns_markdown(tmp_path: Path) -> None:
    """Ensure generate_openssf_checklist delegates to hexaqual and returns Markdown string."""
    adapter = HexaqualRunnerAdapter(repo_root=tmp_path)
    expected_md = "## OpenSSF Passing Checklist\n- [ ] DCO sign-off\n"

    with (
        patch(
            "hexastack_qual.adapters.hexaqual.runner.resolve_local_repo_url",
            return_value="https://github.com/test/repo",
        ),
        patch(
            "hexastack_qual.adapters.hexaqual.runner.evaluate_local_heuristics",
            return_value=[],
        ),
        patch(
            "hexastack_qual.adapters.hexaqual.runner.generate_checklist",
            return_value=[],
        ),
        patch(
            "hexastack_qual.adapters.hexaqual.runner.format_checklist_markdown",
            return_value=expected_md,
        ),
    ):
        checklist = adapter.generate_openssf_checklist(tier="passing")

    assert isinstance(checklist, str)
    assert checklist == expected_md
