"""Unit tests for test_parity utility functions.

Notes/Architectural Intent:
    Verifies that filesystem audits detect missing __init__.py files,
    missing unit tests for source files, and orphaned unit tests.
"""

from pathlib import Path

from hexastack_tools.utils.test_parity import (
    check_package_parity,
    check_src_to_test_symmetry,
    check_test_directories_inits,
)


def test_check_test_directories_inits(tmp_path: Path) -> None:
    """Verify detection of missing __init__.py files in test subdirectories."""
    tests_dir = tmp_path / "tests" / "unit" / "sub"
    tests_dir.mkdir(parents=True)
    errors = check_test_directories_inits(tmp_path)
    assert len(errors) == 2  # missing in unit/ and sub/

    (tmp_path / "tests" / "unit" / "__init__.py").touch()
    (tests_dir / "__init__.py").touch()
    errors_clean = check_test_directories_inits(tmp_path)
    assert errors_clean == []


def test_check_package_parity_clean(tmp_path: Path) -> None:
    """Verify clean 1:1 symmetry between src and tests/unit."""
    pkg_dir = tmp_path / "packages" / "mypkg"
    src_dir = pkg_dir / "src" / "mypkg"
    unit_dir = pkg_dir / "tests" / "unit"
    src_dir.mkdir(parents=True)
    unit_dir.mkdir(parents=True)

    (unit_dir / "__init__.py").touch()
    (src_dir / "__init__.py").touch()
    (src_dir / "mod.py").touch()
    (unit_dir / "test_mod.py").touch()

    errors = check_package_parity(pkg_dir, tmp_path)
    assert errors == []


def test_check_package_parity_missing_and_orphaned(tmp_path: Path) -> None:
    """Verify detection of missing unit tests and orphaned unit tests."""
    pkg_dir = tmp_path / "packages" / "mypkg"
    src_dir = pkg_dir / "src" / "mypkg"
    unit_dir = pkg_dir / "tests" / "unit"
    src_dir.mkdir(parents=True)
    unit_dir.mkdir(parents=True)

    (unit_dir / "__init__.py").touch()
    (src_dir / "untested.py").touch()
    (unit_dir / "test_orphan.py").touch()

    errors = check_package_parity(pkg_dir, tmp_path)
    assert any("Missing unit test" in e for e in errors)
    assert any("Orphaned unit test" in e for e in errors)


def test_check_src_to_test_symmetry_workspace(tmp_path: Path) -> None:
    """Verify check_src_to_test_symmetry iterates across workspace packages."""
    # 1. No packages directory
    assert check_src_to_test_symmetry(tmp_path) == []

    # 2. Package with symmetry issue
    pkg_dir = tmp_path / "packages" / "pkg1"
    src_dir = pkg_dir / "src" / "pkg1"
    unit_dir = pkg_dir / "tests" / "unit"
    src_dir.mkdir(parents=True)
    unit_dir.mkdir(parents=True)
    (unit_dir / "__init__.py").touch()
    (src_dir / "solo.py").touch()

    errors = check_src_to_test_symmetry(tmp_path)
    assert len(errors) == 1
    assert "Missing unit test" in errors[0]
