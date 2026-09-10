"""Unit tests for pytest runner commands."""

from pathlib import Path
from unittest.mock import MagicMock, patch

from hexastack_tools.commands.pytest_runner import (
    archon_generate_main,
    run_main,
)


def test_pytest_runner_callables() -> None:
    """Verify pytest runner callables."""
    assert callable(archon_generate_main)
    assert callable(run_main)


@patch("sys.argv", ["pytest-archon-generate", "-p", "core"])
def test_archon_generate_main(tmp_path: Path) -> None:
    """Verify archon_generate_main generates architecture boundary test."""
    with patch(
        "hexastack_tools.commands.pytest_runner.get_repo_root", return_value=tmp_path
    ):
        pkg_dir = tmp_path / "packages" / "hexastack_core"
        (pkg_dir / "src" / "hexastack_core" / "domain").mkdir(parents=True)
        (pkg_dir / "src" / "hexastack_core" / "ports").mkdir(parents=True)
        (pkg_dir / "pyproject.toml").write_text("[project]\nname = 'hexastack-core'\n")

        archon_generate_main()

        arch_file = pkg_dir / "tests" / "architecture" / "test_hexagonal_boundaries.py"
        assert arch_file.is_file()
        content = arch_file.read_text()
        assert "assert_clean_architecture" in content
        assert "test_hexastack_core_clean_architecture" in content


@patch("subprocess.run", return_value=MagicMock(returncode=0))
@patch("sys.exit")
@patch("sys.argv", ["pytest-run", "--with-context", "-p", "core"])
def test_run_main_with_context(
    mock_exit: MagicMock, mock_subproc: MagicMock, tmp_path: Path
) -> None:
    """Verify run_main forwards -n 0 and --cov-context=test when --with-context is enabled."""
    with patch(
        "hexastack_tools.commands.pytest_runner.get_repo_root", return_value=tmp_path
    ):
        pkg_dir = tmp_path / "packages" / "hexastack_core"
        (pkg_dir / "src").mkdir(parents=True)
        (pkg_dir / "tests").mkdir(parents=True)
        run_main()
        mock_subproc.assert_called_once()
        cmd_args = mock_subproc.call_args[0][0]
        assert "-n" in cmd_args
        assert "0" in cmd_args
        assert "--cov-context=test" in cmd_args


@patch("subprocess.run", return_value=MagicMock(returncode=0))
@patch("sys.exit")
@patch("sys.argv", ["pytest-run", "-e", "financial-ledger"])
def test_run_main_with_example(
    mock_exit: MagicMock, mock_subproc: MagicMock, tmp_path: Path
) -> None:
    """Verify run_main resolves example test path and adds src to sys.path."""
    with patch(
        "hexastack_tools.commands.pytest_runner.get_repo_root", return_value=tmp_path
    ):
        ex_dir = tmp_path / "examples" / "financial-ledger"
        (ex_dir / "src" / "financial_ledger").mkdir(parents=True)
        (ex_dir / "tests").mkdir(parents=True)
        run_main()
        mock_subproc.assert_called_once()
        cmd_args = mock_subproc.call_args[0][0]
        assert str(ex_dir / "tests") in cmd_args
        assert "--no-cov" in cmd_args


@patch("subprocess.run", return_value=MagicMock(returncode=0))
@patch("sys.exit")
@patch(
    "hexastack_tools.commands.pytest_runner._get_git_changed_files",
    return_value=["packages/hexastack_core/src/hexastack_core/models.py"],
)
@patch("sys.argv", ["pytest-run", "-A", "-U"])
def test_run_main_with_affected(
    mock_git: MagicMock, mock_exit: MagicMock, mock_subproc: MagicMock, tmp_path: Path
) -> None:
    """Verify run_main resolves affected package test path when -A is passed."""
    with patch(
        "hexastack_tools.commands.pytest_runner.get_repo_root", return_value=tmp_path
    ):
        pkg_dir = tmp_path / "packages" / "hexastack_core"
        (pkg_dir / "src" / "hexastack_core").mkdir(parents=True)
        (pkg_dir / "tests" / "unit").mkdir(parents=True)
        (pkg_dir / "pyproject.toml").write_text("[project]\nname = 'hexastack-core'\n")
        run_main()
        mock_subproc.assert_called_once()
        cmd_args = mock_subproc.call_args[0][0]
        assert str(pkg_dir / "tests" / "unit") in cmd_args
        assert "--cov-reset" in cmd_args
