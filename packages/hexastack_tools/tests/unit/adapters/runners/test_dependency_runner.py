"""Unit tests for SubprocessDependencyAuditorAdapter.

Notes/Architectural Intent:
    Verifies that SubprocessDependencyAuditorAdapter properly delegates
    to subprocess commands, parser utilities, and workspace discovery.
"""

from pathlib import Path
from unittest.mock import MagicMock, patch

from hexastack_tools.adapters.runners.dependency_runner import (
    SubprocessDependencyAuditorAdapter,
)


def test_audit_extras_parity(tmp_path: Path):
    """Verify audit_extras_parity returns ExtrasAuditResult."""
    adapter = SubprocessDependencyAuditorAdapter()
    with (
        patch(
            "hexastack_tools.adapters.runners.dependency_runner.check_extras",
            return_value=[],
        ),
        patch(
            "hexastack_tools.adapters.runners.dependency_runner.get_package_directories",
            return_value=[tmp_path],
        ),
    ):
        res = adapter.audit_extras_parity(tmp_path)
        assert res.is_healthy is True
        assert res.total_packages_checked == 1


def test_generate_extras_diagram(tmp_path: Path):
    """Verify generate_extras_diagram calls utility."""
    adapter = SubprocessDependencyAuditorAdapter()
    with patch(
        "hexastack_tools.adapters.runners.dependency_runner.make_mermaid",
        return_value="graph LR",
    ):
        diagram = adapter.generate_extras_diagram(tmp_path)
        assert diagram == "graph LR"


def test_run_deptry_package(tmp_path: Path):
    """Verify run_deptry runs subprocess and parses output."""
    adapter = SubprocessDependencyAuditorAdapter()

    # Missing pyproject
    res_missing = adapter.run_deptry(tmp_path)
    assert res_missing.passed is True

    # With pyproject, success
    (tmp_path / "pyproject.toml").touch()
    mock_res_ok = MagicMock(returncode=0)
    with patch("subprocess.run", return_value=mock_res_ok):
        res_ok = adapter.run_deptry(tmp_path)
        assert res_ok.passed is True

    # With pyproject, failure
    mock_res_fail = MagicMock(returncode=1, stdout="DEP001 missing", stderr="")
    with patch("subprocess.run", return_value=mock_res_fail):
        res_fail = adapter.run_deptry(tmp_path)
        assert res_fail.passed is False
        assert "DEP001" in res_fail.error_output


def test_run_import_linter(tmp_path: Path):
    """Verify run_import_linter runs lint-imports subprocess."""
    adapter = SubprocessDependencyAuditorAdapter()

    # Missing pyproject
    assert adapter.run_import_linter(tmp_path).passed is True

    # With pyproject, success
    (tmp_path / "pyproject.toml").touch()
    mock_ok = MagicMock(returncode=0)
    with patch("subprocess.run", return_value=mock_ok):
        assert adapter.run_import_linter(tmp_path).passed is True

    # With pyproject, failure
    mock_fail = MagicMock(returncode=1, stdout="Contract broken", stderr="")
    with patch("subprocess.run", return_value=mock_fail):
        res_fail = adapter.run_import_linter(tmp_path)
        assert res_fail.passed is False
        assert "Contract broken" in res_fail.error_output


def test_generate_config_and_tool_avail(tmp_path: Path):
    """Verify generate_import_linter_config and check_tool_availability."""
    adapter = SubprocessDependencyAuditorAdapter()

    with patch(
        "hexastack_tools.adapters.runners.dependency_runner.update_pyproject_toml",
        return_value=True,
    ):
        assert adapter.generate_import_linter_config(tmp_path) is True

    with patch(
        "hexastack_tools.adapters.runners.dependency_runner.generate_all_diagrams"
    ) as mock_diag:
        adapter.generate_architecture_diagrams(tmp_path)
        mock_diag.assert_called_once_with(tmp_path)

    with patch(
        "hexastack_tools.adapters.runners.dependency_runner.check_tool_avail",
        return_value=(True, ""),
    ):
        ok, _ = adapter.check_tool_availability("deptry")
        assert ok is True
