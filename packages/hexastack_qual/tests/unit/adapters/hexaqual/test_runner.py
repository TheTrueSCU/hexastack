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
