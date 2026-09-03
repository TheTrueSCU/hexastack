"""Unit tests for deps-audit unified dependency tool."""

from __future__ import annotations

from hexastack_tools.commands.deps_audit import (
    audit_workspace_dependencies,
    main,
)
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
        generate_diagrams=False,
    )
    assert is_healthy is True
    assert errors == []
