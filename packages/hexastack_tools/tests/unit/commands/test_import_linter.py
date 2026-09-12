"""Unit tests for import_linter commands."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

from hexastack_tools.commands.import_linter import (
    build_import_linter_toml,
    generate_main,
    run_main,
    update_pyproject_toml,
)
from hexastack_tools.domain.dependencies import (
    GenerateImportLinterConfigCommand,
    ImportLinterReport,
    RunImportLinterCommand,
)
from hexastack_tools.ports.dependencies import DependencyPresenterPort


def test_import_linter_callables() -> None:
    """Verify import linter callables and re-exports."""
    assert callable(build_import_linter_toml)
    assert callable(generate_main)
    assert callable(run_main)
    assert callable(update_pyproject_toml)


def test_generate_main_dispatches(tmp_path: Path) -> None:
    """Verify generate_main dispatches GenerateImportLinterConfigCommand."""
    mock_bus = MagicMock()
    with (
        patch(
            "hexastack_tools.commands.import_linter.get_repo_root",
            return_value=tmp_path,
        ),
        patch(
            "hexastack_tools.commands.import_linter.create_governance_bus",
            return_value=mock_bus,
        ),
    ):
        generate_main([])
        mock_bus.dispatch.assert_called_once()
        cmd = mock_bus.dispatch.call_args[0][0]
        assert isinstance(cmd, GenerateImportLinterConfigCommand)
        assert cmd.repo_root == tmp_path


def test_run_main_dispatches_and_presents(tmp_path: Path) -> None:
    """Verify run_main dispatches RunImportLinterCommand and delegates to presenter."""
    pkg_dir = tmp_path / "pkg"
    pkg_dir.mkdir()
    (pkg_dir / "pyproject.toml").write_text("[project]\nname = 'pkg'\n")

    mock_bus = MagicMock()
    mock_bus.dispatch.return_value = ImportLinterReport(results=(), exit_code=0)
    mock_presenter = MagicMock(spec=DependencyPresenterPort)
    mock_presenter.present_import_linter.return_value = 0

    with (
        patch("hexastack_tools.commands.import_linter.ensure_tool_installed"),
        patch(
            "hexastack_tools.commands.import_linter.get_repo_root",
            return_value=tmp_path,
        ),
        patch(
            "hexastack_tools.commands.import_linter.get_packages_directory",
            return_value=tmp_path,
        ),
        patch(
            "hexastack_tools.commands.import_linter.get_package_directories",
            return_value=[pkg_dir],
        ),
        patch(
            "hexastack_tools.commands.import_linter.create_governance_bus",
            return_value=mock_bus,
        ),
        patch(
            "hexastack_tools.commands.import_linter.create_dependency_presenter",
            return_value=mock_presenter,
        ) as mock_create_presenter,
    ):
        exit_code = run_main(["--all", "-f", "json"])
        assert exit_code == 0
        mock_create_presenter.assert_called_once_with("json")
        mock_bus.dispatch.assert_called_once()
        cmd = mock_bus.dispatch.call_args[0][0]
        assert isinstance(cmd, RunImportLinterCommand)
        assert cmd.all_packages is True
        mock_presenter.present_import_linter.assert_called_once_with(
            mock_bus.dispatch.return_value
        )


def test_run_main_no_targets(tmp_path: Path) -> None:
    """Verify run_main returns 0 immediately when no targets match."""
    with (
        patch("hexastack_tools.commands.import_linter.ensure_tool_installed"),
        patch(
            "hexastack_tools.commands.import_linter.get_packages_directory",
            return_value=tmp_path,
        ),
        patch(
            "hexastack_tools.commands.import_linter.get_package_directories",
            return_value=[],
        ),
    ):
        exit_code = run_main(["nonexistent.py"])
        assert exit_code == 0
