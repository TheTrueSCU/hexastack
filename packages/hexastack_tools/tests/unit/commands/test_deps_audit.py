"""Unit tests for deps-audit unified dependency tool."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

from hexastack_tools.commands.deps_audit import (
    audit_workspace_dependencies,
    main,
)
from hexastack_tools.domain.dependencies import (
    RunUnifiedDepsAuditCommand,
    UnifiedDependencyAuditReport,
)
from hexastack_tools.ports.dependencies import DependencyPresenterPort
from hexastack_tools.utils.workspace import get_repo_root


def test_deps_audit_callables_exist() -> None:
    """Verify deps-audit exports are defined and callable."""
    assert callable(audit_workspace_dependencies)
    assert callable(main)


def test_audit_workspace_dependencies_passes_on_current_workspace() -> None:
    """Verify that current workspace passes the unified deps audit."""
    repo_root = get_repo_root()
    is_healthy, errors = audit_workspace_dependencies(
        repo_root,
        check_deptry=True,
        check_extras=True,
        check_tools=True,
        generate_diagrams=False,
    )
    assert is_healthy is True
    assert errors == []


def test_main_dispatches_and_presents() -> None:
    """Verify main dispatches RunUnifiedDepsAuditCommand and delegates to presenter."""
    mock_bus = MagicMock()
    mock_bus.dispatch.return_value = UnifiedDependencyAuditReport(
        items=(),
        errors=(),
        is_healthy=True,
    )
    mock_presenter = MagicMock(spec=DependencyPresenterPort)
    mock_presenter.present_unified_deps_audit.return_value = 0

    with (
        patch(
            "hexastack_tools.commands.deps_audit.create_governance_bus",
            return_value=mock_bus,
        ),
        patch(
            "hexastack_tools.commands.deps_audit.create_dependency_presenter",
            return_value=mock_presenter,
        ) as mock_create_presenter,
    ):
        exit_code = main(["-f", "markdown", "--deptry-only"])
        assert exit_code == 0
        mock_create_presenter.assert_called_once_with("markdown")
        mock_bus.dispatch.assert_called_once()
        cmd = mock_bus.dispatch.call_args[0][0]
        assert isinstance(cmd, RunUnifiedDepsAuditCommand)
        assert cmd.check_deptry is True
        assert cmd.check_extras is False
        mock_presenter.present_unified_deps_audit.assert_called_once_with(
            mock_bus.dispatch.return_value
        )
