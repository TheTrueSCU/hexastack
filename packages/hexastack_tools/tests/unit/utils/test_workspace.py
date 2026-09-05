import tempfile
from pathlib import Path

import pytest

from hexastack_tools.utils.workspace import (
    check_tool_availability,
    ensure_tool_installed,
    get_package_directories,
    get_package_directory,
    get_package_module_dir,
    get_packages_directory,
    get_present_layers,
    get_repo_root,
    get_valid_package_names,
)


def test_check_tool_availability_existing() -> None:
    """Verify check_tool_availability for installed package."""
    is_ok, err = check_tool_availability("rich")
    assert is_ok is True
    assert err == ""


def test_check_tool_availability_missing() -> None:
    """Verify check_tool_availability for non-existent package."""
    is_ok, err = check_tool_availability("non_existent_package_xyz_99")
    assert is_ok is False
    assert "not installed" in err


def test_ensure_tool_installed_raises_system_exit_on_missing() -> None:
    """Verify ensure_tool_installed exits with error code 1 when missing."""
    with pytest.raises(SystemExit) as exc_info:
        ensure_tool_installed("non_existent_tool_123", extra_name="test-extra")
    assert exc_info.value.code == 1


def test_get_repo_root() -> None:
    """Verify repo root discovery."""
    root = get_repo_root()
    assert (root / "pyproject.toml").is_file()


def test_get_packages_directory() -> None:
    """Verify packages directory resolution."""
    pkg_dir = get_packages_directory()
    assert pkg_dir.is_dir()
    assert pkg_dir.name == "packages"


def test_get_package_directory() -> None:
    """Verify individual package path resolution."""
    core_dir = get_package_directory("core")
    assert core_dir.name == "hexastack_core"
    assert core_dir.is_dir()


def test_get_package_directories() -> None:
    """Verify list of package directories contains known packages."""
    dirs = get_package_directories()
    names = {d.name for d in dirs}
    assert "hexastack_core" in names
    assert "hexastack_tools" in names


def test_get_valid_package_names() -> None:
    """Verify dynamic valid package name enumeration."""
    names = get_valid_package_names()
    assert "core" in names
    assert "hexastack_core" in names
    assert "tools" in names


def test_get_package_module_dir() -> None:
    """Verify detection of internal module directory under src/."""
    core_dir = get_package_directory("core")
    mod_dir = get_package_module_dir(core_dir)
    assert mod_dir is not None
    assert mod_dir.name == "hexastack_core"


def test_get_present_layers() -> None:
    """Verify detection of hexagonal layers."""
    core_dir = get_package_directory("core")
    layers = get_present_layers(core_dir)
    assert "domain" in layers
    assert "ports" in layers
    assert "adapters" in layers


def test_standalone_single_package_workspace_discovery() -> None:
    """Verify workspace tools function in a standalone single-package repo."""
    with tempfile.TemporaryDirectory() as tmpdir:
        root = Path(tmpdir)
        (root / "pyproject.toml").write_text(
            '[project]\nname = "my-service"\n', encoding="utf-8"
        )
        src_dir = root / "src" / "my_service" / "domain"
        src_dir.mkdir(parents=True)
        (src_dir / "models.py").write_text("# domain model", encoding="utf-8")

        discovered_dirs = get_package_directories(repo_root=root)
        assert len(discovered_dirs) == 1
        assert discovered_dirs[0] == root

        pkg_dir = get_package_directory("my-service", repo_root=root)
        assert pkg_dir == root

        mod_dir = get_package_module_dir(root)
        assert mod_dir is not None
        assert mod_dir.name == "my_service"

        layers = get_present_layers(root)
        assert "domain" in layers


def test_custom_monorepo_workspace_discovery() -> None:
    """Verify workspace tools discover custom monorepo members like hexaqueue."""
    with tempfile.TemporaryDirectory() as tmpdir:
        root = Path(tmpdir)
        pyproject_content = """[tool.uv.workspace]
members = [
    "services/*",
]
"""
        (root / "pyproject.toml").write_text(pyproject_content, encoding="utf-8")

        for s in ("hq_server", "hq_worker"):
            pkg_path = root / "services" / s
            (pkg_path / "src" / s / "domain").mkdir(parents=True)
            (pkg_path / "pyproject.toml").write_text(
                f'[project]\nname = "{s}"\n', encoding="utf-8"
            )

        discovered_dirs = get_package_directories(repo_root=root)
        assert len(discovered_dirs) == 2
        dir_names = {d.name for d in discovered_dirs}
        assert dir_names == {"hq_server", "hq_worker"}

        server_dir = get_package_directory("hq_server", repo_root=root)
        assert server_dir.name == "hq_server"
