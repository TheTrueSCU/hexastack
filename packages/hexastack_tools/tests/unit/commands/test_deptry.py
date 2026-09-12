"""Unit tests for deptry command."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

from hexastack_tools.commands.deptry import main, run_deptry_on_package
from hexastack_tools.domain.dependencies import DeptryAuditReport, RunDeptryAuditCommand
from hexastack_tools.ports.dependencies import DependencyPresenterPort


def test_deptry_main_callable() -> None:
    """Verify deptry main and helper callables."""
    assert callable(main)
    assert callable(run_deptry_on_package)


def test_run_deptry_on_package(tmp_path: Path) -> None:
    """Verify run_deptry_on_package invokes adapter."""
    with patch(
        "hexastack_tools.commands.deptry.SubprocessDependencyAuditorAdapter"
    ) as mock_cls:
        mock_instance = MagicMock()
        mock_cls.return_value = mock_instance
        mock_instance.run_deptry.return_value = MagicMock(passed=True, error_output="")

        ok, err = run_deptry_on_package(tmp_path)
        assert ok is True
        assert err == ""
        mock_instance.run_deptry.assert_called_once_with(tmp_path)


def test_deptry_main_dispatches_and_presents() -> None:
    """Verify main dispatches RunDeptryAuditCommand and delegates to presenter."""
    mock_bus = MagicMock()
    mock_bus.dispatch.return_value = DeptryAuditReport(results=(), exit_code=0)
    mock_presenter = MagicMock(spec=DependencyPresenterPort)
    mock_presenter.present_deptry_audit.return_value = 0

    with (
        patch("hexastack_tools.commands.deptry.ensure_tool_installed"),
        patch(
            "hexastack_tools.commands.deptry.create_governance_bus",
            return_value=mock_bus,
        ),
        patch(
            "hexastack_tools.commands.deptry.create_dependency_presenter",
            return_value=mock_presenter,
        ) as mock_create_presenter,
    ):
        exit_code = main(["-f", "markdown"])
        assert exit_code == 0
        mock_create_presenter.assert_called_once_with("markdown")
        mock_bus.dispatch.assert_called_once()
        cmd = mock_bus.dispatch.call_args[0][0]
        assert isinstance(cmd, RunDeptryAuditCommand)
        mock_presenter.present_deptry_audit.assert_called_once_with(
            mock_bus.dispatch.return_value
        )
