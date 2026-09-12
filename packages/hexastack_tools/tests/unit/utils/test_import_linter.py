"""Unit tests for import_linter utility functions.

Notes/Architectural Intent:
    Verifies generation of [tool.importlinter] layer hierarchies and forbidden contracts.
"""

from pathlib import Path

from hexastack_tools.utils.import_linter import (
    build_import_linter_toml,
    update_pyproject_toml,
)


def test_build_import_linter_toml():
    """Verify build_import_linter_toml produces valid TOML with layers and contracts."""
    pkg_name = "test_pkg"
    present = {"domain", "ports", "adapters", "infra"}
    toml_str = build_import_linter_toml(pkg_name, present)
    assert "[tool.importlinter]" in toml_str
    assert 'root_packages = ["test_pkg"]' in toml_str
    assert 'name = "Hexagonal architecture layer hierarchy"' in toml_str
    assert '"infra"' in toml_str
    assert '"domain"' in toml_str


def test_update_pyproject_toml(tmp_path: Path):
    """Verify update_pyproject_toml updates existing file."""
    # 1. Missing file returns False
    assert update_pyproject_toml(tmp_path / "nonexistent") is False

    # 2. Package without layers
    pkg_dir = tmp_path / "mypkg"
    pkg_dir.mkdir()
    pyproject = pkg_dir / "pyproject.toml"
    pyproject.write_text("[project]\nname = 'mypkg'\n", encoding="utf-8")
    assert update_pyproject_toml(pkg_dir) is False

    # 3. Package with layers
    src_dir = pkg_dir / "src" / "mypkg"
    (src_dir / "domain").mkdir(parents=True)
    (src_dir / "ports").mkdir(parents=True)
    assert update_pyproject_toml(pkg_dir) is True
    content = pyproject.read_text(encoding="utf-8")
    assert "[tool.importlinter]" in content
