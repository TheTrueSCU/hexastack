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


@patch("pytest.main", return_value=0)
@patch("sys.exit")
@patch("sys.argv", ["pytest-run", "--with-context", "-p", "core"])
def test_run_main_with_context(
    mock_exit: MagicMock, mock_pytest: MagicMock, tmp_path: Path
) -> None:
    """Verify run_main forwards -n 0 and --cov-context=test when --with-context is enabled."""
    with patch(
        "hexastack_tools.commands.pytest_runner.get_repo_root", return_value=tmp_path
    ):
        pkg_dir = tmp_path / "packages" / "hexastack_core"
        (pkg_dir / "src").mkdir(parents=True)
        (pkg_dir / "tests").mkdir(parents=True)
        run_main()
        mock_pytest.assert_called_once()
        call_args = mock_pytest.call_args[0][0]
        assert "-n" in call_args
        assert "0" in call_args
        assert "--cov-context=test" in call_args
