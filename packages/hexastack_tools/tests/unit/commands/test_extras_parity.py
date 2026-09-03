"""Unit tests for check-extras-parity tool command."""

from __future__ import annotations

from pathlib import Path

from hexastack_tools.commands.extras_parity import (
    audit_extras_parity,
    main,
)
from hexastack_tools.utils.workspace import get_repo_root


def test_extras_parity_callables_exist() -> None:
    """Verify extras parity validator exports are defined and callable."""
    assert callable(audit_extras_parity)
    assert callable(main)


def test_audit_extras_parity_passes_on_current_workspace() -> None:
    """Verify that current repository workspace has 100% extras parity."""
    repo_root = get_repo_root()
    violations = audit_extras_parity(repo_root)
    assert violations == []


def test_audit_extras_parity_flags_missing_umbrella_file(tmp_path: Path) -> None:
    """Verify validator flags missing umbrella pyproject.toml."""
    violations = audit_extras_parity(tmp_path)
    assert len(violations) == 1
    assert violations[0].extra_name == "<root>"
