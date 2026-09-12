"""Unit tests for PyPI command handlers."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock

import pytest

from hexastack_tools.domain.pypi import (
    BuildPackagesCommand,
    CheckPyPiReleasesCommand,
    PackageMetadata,
    PublishPackagesCommand,
    PyPiBuildReport,
    PyPiCheckReport,
    PyPiPublishReport,
    ReproducibleBuildReport,
    VerifyReproducibleBuildCommand,
)
from hexastack_tools.infra.handlers.pypi import (
    BuildPackagesHandler,
    CheckPyPiReleasesHandler,
    PublishPackagesHandler,
    VerifyReproducibleBuildHandler,
    discover_workspace_packages,
    find_package_dist_files,
)


@pytest.fixture
def mock_client() -> MagicMock:
    """Create mock PyPiClientPort."""
    return MagicMock()


@pytest.fixture
def sample_workspace(tmp_path: Path) -> Path:
    """Create a sample workspace layout with two packages."""
    pkg1 = tmp_path / "packages" / "pkg_a"
    pkg1.mkdir(parents=True)
    (pkg1 / "pyproject.toml").write_text(
        '[project]\nname = "pkg-a"\nversion = "1.0.0"\n', encoding="utf-8"
    )

    pkg2 = tmp_path / "packages" / "pkg_b"
    pkg2.mkdir(parents=True)
    (pkg2 / "pyproject.toml").write_text(
        '[project]\nname = "pkg-b"\nversion = "2.0.0"\n', encoding="utf-8"
    )

    # Empty or invalid pyproject
    pkg_invalid = tmp_path / "packages" / "pkg_invalid"
    pkg_invalid.mkdir(parents=True)
    (pkg_invalid / "pyproject.toml").write_text("invalid toml [", encoding="utf-8")

    return tmp_path


def test_discover_workspace_packages(sample_workspace: Path) -> None:
    """Test discovering workspace package metadata from pyproject.toml."""
    packages = discover_workspace_packages(sample_workspace)
    assert len(packages) == 2
    assert packages[0].name == "pkg-a"
    assert packages[0].version == "1.0.0"
    assert packages[1].name == "pkg-b"
    assert packages[1].version == "2.0.0"


def test_find_package_dist_files(tmp_path: Path) -> None:
    """Test finding built distribution files with hyphen and underscore variants."""
    dist_dir = tmp_path / "dist"
    dist_dir.mkdir()

    f1 = dist_dir / "my_pkg-1.0.0-py3-none-any.whl"
    f1.write_text("wheel", encoding="utf-8")
    f2 = dist_dir / "my-pkg-1.0.0.tar.gz"
    f2.write_text("sdist", encoding="utf-8")
    other = dist_dir / "other_pkg-1.0.0.whl"
    other.write_text("other", encoding="utf-8")

    pkg = PackageMetadata(
        name="my-pkg",
        version="1.0.0",
        dir_path=tmp_path,
        pyproject_path=tmp_path / "pyproject.toml",
    )

    found = find_package_dist_files(dist_dir, pkg)
    assert len(found) == 2
    assert f1 in found
    assert f2 in found
    assert other not in found


def test_check_pypi_releases_handler(
    mock_client: MagicMock, sample_workspace: Path
) -> None:
    """Test CheckPyPiReleasesHandler with all packages and filtered by name."""
    mock_client.check_version_exists.side_effect = lambda name, ver: name == "pkg-a"

    handler = CheckPyPiReleasesHandler(mock_client, repo_root=sample_workspace)

    # All packages
    rep1 = handler.handle(CheckPyPiReleasesCommand())
    assert isinstance(rep1, PyPiCheckReport)
    assert len(rep1.checks) == 2
    assert rep1.checks[0].package.name == "pkg-a"
    assert rep1.checks[0].exists is True
    assert rep1.checks[1].package.name == "pkg-b"
    assert rep1.checks[1].exists is False

    # Filtered by package name
    rep2 = handler.handle(CheckPyPiReleasesCommand(package_name="pkg-a"))
    assert len(rep2.checks) == 1
    assert rep2.checks[0].package.name == "pkg-a"


def test_build_packages_handler(
    mock_client: MagicMock, sample_workspace: Path, tmp_path: Path
) -> None:
    """Test BuildPackagesHandler orchestrating builds."""
    mock_client.build_package.return_value = (True, "Built successfully")

    handler = BuildPackagesHandler(mock_client, repo_root=sample_workspace)
    target_dist = tmp_path / "custom_dist"

    report = handler.handle(
        BuildPackagesCommand(target_dist=target_dist, package_name="pkg-a")
    )
    assert isinstance(report, PyPiBuildReport)
    assert report.has_failure is False
    assert len(report.results) == 1
    assert report.results[0].package.name == "pkg-a"
    assert report.results[0].success is True
    mock_client.build_package.assert_called_once_with("pkg-a", target_dist)


def test_publish_packages_handler_full_flow(
    mock_client: MagicMock, sample_workspace: Path, tmp_path: Path
) -> None:
    """Test PublishPackagesHandler covering publish, skip, and error cases."""
    dist_dir = tmp_path / "dist"
    dist_dir.mkdir()

    # Create dist file for pkg-a
    f_a = dist_dir / "pkg_a-1.0.0-py3-none-any.whl"
    f_a.write_text("a", encoding="utf-8")

    # pkg-a succeeds, pkg-b has no dist files
    mock_client.check_version_exists.return_value = False
    mock_client.publish_package.return_value = (True, "published")

    handler = PublishPackagesHandler(mock_client, repo_root=sample_workspace)
    cmd = PublishPackagesCommand(
        dist_dir=dist_dir, token="tok", delay=0.0, skip_existing=True
    )
    report = handler.handle(cmd)

    assert isinstance(report, PyPiPublishReport)
    assert len(report.results) == 2
    assert report.results[0].package.name == "pkg-a"
    assert report.results[0].outcome == "published"
    assert report.results[0].is_success is True

    assert report.results[1].package.name == "pkg-b"
    assert report.results[1].outcome == "failed"
    assert "No dist files found" in report.results[1].detail


def test_publish_packages_handler_skip_and_error_branches(
    mock_client: MagicMock, sample_workspace: Path, tmp_path: Path
) -> None:
    """Test PublishPackagesHandler rate limit, already exists, and build_first error."""
    dist_dir = tmp_path / "dist"
    dist_dir.mkdir()
    f_a = dist_dir / "pkg_a-1.0.0.whl"
    f_a.write_text("a", encoding="utf-8")

    handler = PublishPackagesHandler(mock_client, repo_root=sample_workspace)

    # 1. Skip because check_version_exists returns True
    mock_client.check_version_exists.return_value = True
    rep_skip = handler.handle(
        PublishPackagesCommand(
            dist_dir=dist_dir, package_name="pkg-a", skip_existing=True
        )
    )
    assert rep_skip.results[0].outcome == "skipped"

    # 2. Already exists outcome from upload
    mock_client.check_version_exists.return_value = False
    mock_client.publish_package.return_value = (False, "already_exists")
    rep_exists = handler.handle(
        PublishPackagesCommand(dist_dir=dist_dir, package_name="pkg-a")
    )
    assert rep_exists.results[0].outcome == "skipped"

    # 3. Rate limited outcome from upload
    mock_client.publish_package.return_value = (False, "rate_limited")
    rep_rate = handler.handle(
        PublishPackagesCommand(dist_dir=dist_dir, package_name="pkg-a")
    )
    assert rep_rate.results[0].outcome == "failed"
    assert "Rate Limited" in rep_rate.results[0].detail

    # 4. build_first fails
    mock_client.build_package.return_value = (False, "Build failed")
    rep_build_fail = handler.handle(
        PublishPackagesCommand(
            dist_dir=dist_dir, package_name="pkg-a", build_first=True
        )
    )
    assert rep_build_fail.has_failure is True
    assert "Build failed before publish" in rep_build_fail.results[0].detail


def test_verify_reproducible_build_handler(
    mock_client: MagicMock, sample_workspace: Path
) -> None:
    """Test VerifyReproducibleBuildHandler comparing builds across temp directories."""
    handler = VerifyReproducibleBuildHandler(mock_client, repo_root=sample_workspace)

    # Build success producing matching files
    def fake_build(name: str, out_dir: Path, env: dict[str, str] | None = None):
        whl = out_dir / f"{name}-1.0.0.whl"
        whl.write_bytes(b"deterministic-bytes")
        return True, "ok"

    mock_client.build_package.side_effect = fake_build
    cmd = VerifyReproducibleBuildCommand(
        package_name="pkg-a", source_date_epoch="1700000000"
    )
    report = handler.handle(cmd)

    assert isinstance(report, ReproducibleBuildReport)
    assert report.epoch == "1700000000"
    assert report.all_matched is True
    assert len(report.results) == 1
    assert report.results[0].is_reproducible is True


def test_verify_reproducible_build_handler_failures(
    mock_client: MagicMock, sample_workspace: Path
) -> None:
    """Test VerifyReproducibleBuildHandler with build errors and missing files."""
    handler = VerifyReproducibleBuildHandler(mock_client, repo_root=sample_workspace)

    # Build failure
    mock_client.build_package.return_value = (False, "compiler crashed")
    rep_fail = handler.handle(VerifyReproducibleBuildCommand(package_name="pkg-a"))
    assert rep_fail.all_matched is False
    assert rep_fail.results[0].hash1 == "build_error"
