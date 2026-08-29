"""Unit tests for workspace utilities."""

from hexastack_tools.utils.workspace import (
    get_package_directories,
    get_package_directory,
    get_packages_directory,
    get_repo_root,
)


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
