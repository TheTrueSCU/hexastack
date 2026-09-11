"""Command handlers for PyPI builds, release checks, publishing, and reproducible audits.

Notes/Architectural Intent:
    Decouples driving CLI commands from PyPiClientPort implementations and implements
    the core business workflows for monorepo package release management.
"""

from __future__ import annotations

import hashlib
import os
import tempfile
import time
import tomllib
from pathlib import Path

from hexastack_tools.domain.pypi import (
    BuildPackagesCommand,
    CheckPyPiReleasesCommand,
    PackageBuildResult,
    PackageMetadata,
    PackagePublishResult,
    PackageReleaseCheck,
    PublishPackagesCommand,
    PyPiBuildReport,
    PyPiCheckReport,
    PyPiPublishReport,
    ReproducibleArtifactResult,
    ReproducibleBuildReport,
    VerifyReproducibleBuildCommand,
)
from hexastack_tools.ports.pypi import PyPiClientPort
from hexastack_tools.utils.workspace import get_package_directories, get_repo_root

__all__ = [
    "BuildPackagesHandler",
    "CheckPyPiReleasesHandler",
    "discover_workspace_packages",
    "find_package_dist_files",
    "PublishPackagesHandler",
    "VerifyReproducibleBuildHandler",
]


def discover_workspace_packages(repo_root: Path | None = None) -> list[PackageMetadata]:
    """Discover all packages in the workspace and extract metadata from pyproject.toml.

    Args:
        repo_root: Optional repository root path.

    Returns:
        Sorted list of PackageMetadata domain models.

    Notes/Architectural Intent:
        Scans workspace package directories dynamically to identify publishable packages.
    """
    root = repo_root or get_repo_root()
    pkg_dirs = get_package_directories(root)
    packages: list[PackageMetadata] = []

    for pkg_dir in pkg_dirs:
        pyproject = pkg_dir / "pyproject.toml"
        if not pyproject.is_file():
            continue

        try:
            content = tomllib.loads(pyproject.read_text(encoding="utf-8"))
            project = content.get("project", {})
            name = project.get("name")
            version = project.get("version")
            if name and version:
                packages.append(
                    PackageMetadata(
                        name=name,
                        version=version,
                        dir_path=pkg_dir,
                        pyproject_path=pyproject,
                    )
                )
        except Exception:
            continue

    return sorted(packages, key=lambda p: p.name)


def find_package_dist_files(target_dist: Path, pkg: PackageMetadata) -> list[Path]:
    """Locate built wheel/sdist distributions for a package in target dist directory.

    Args:
        target_dist: Directory containing built package distribution files.
        pkg: Target PackageMetadata domain model.

    Returns:
        Deduplicated list of matching artifact file paths.

    Notes/Architectural Intent:
        Matches both hyphenated and normalized underscore package distribution filenames.
    """
    pkg_underscore = pkg.name.replace("-", "_")
    dist_files = list(target_dist.glob(f"{pkg_underscore}-{pkg.version}*")) + list(
        target_dist.glob(f"{pkg.name}-{pkg.version}*")
    )
    return list({f.resolve(): f for f in dist_files}.values())


class CheckPyPiReleasesHandler:
    """Handler verifying package release version availability against PyPI index."""

    def __init__(self, client: PyPiClientPort, repo_root: Path | None = None) -> None:
        """Initialize handler with PyPI client port and repo root.

        Args:
            client: PyPiClientPort adapter instance.
            repo_root: Optional workspace root directory.
        """
        self._client = client
        self._repo_root = repo_root or get_repo_root()

    def handle(self, command: CheckPyPiReleasesCommand) -> PyPiCheckReport:
        """Handle CheckPyPiReleasesCommand.

        Args:
            command: CheckPyPiReleasesCommand instance.

        Returns:
            PyPiCheckReport with package availability findings.
        """
        packages = (
            list(command.packages)
            if command.packages is not None
            else discover_workspace_packages(self._repo_root)
        )
        if command.package_name:
            packages = [p for p in packages if p.name == command.package_name]

        checks: list[PackageReleaseCheck] = []
        for pkg in packages:
            exists = self._client.check_version_exists(pkg.name, pkg.version)
            checks.append(PackageReleaseCheck(package=pkg, exists=exists))

        return PyPiCheckReport(checks=tuple(checks))


class BuildPackagesHandler:
    """Handler orchestrating package distribution builds via uv build."""

    def __init__(self, client: PyPiClientPort, repo_root: Path | None = None) -> None:
        """Initialize handler with PyPI client port and repo root.

        Args:
            client: PyPiClientPort adapter instance.
            repo_root: Optional workspace root directory.
        """
        self._client = client
        self._repo_root = repo_root or get_repo_root()

    def handle(self, command: BuildPackagesCommand) -> PyPiBuildReport:
        """Handle BuildPackagesCommand.

        Args:
            command: BuildPackagesCommand specifying optional target directory and package.

        Returns:
            PyPiBuildReport summarizing build outcomes across packages.
        """
        target_dist = command.target_dist or (self._repo_root / "dist")
        target_dist.mkdir(parents=True, exist_ok=True)

        packages = (
            list(command.packages)
            if command.packages is not None
            else discover_workspace_packages(self._repo_root)
        )
        if command.package_name:
            packages = [p for p in packages if p.name == command.package_name]

        results: list[PackageBuildResult] = []
        for pkg in packages:
            ok, output = self._client.build_package(pkg.name, target_dist)
            results.append(PackageBuildResult(package=pkg, success=ok, output=output))

        return PyPiBuildReport(target_dist=target_dist, results=tuple(results))


class PublishPackagesHandler:
    """Handler publishing built distribution artifacts to PyPI."""

    def __init__(self, client: PyPiClientPort, repo_root: Path | None = None) -> None:
        """Initialize handler with PyPI client port and repo root.

        Args:
            client: PyPiClientPort adapter instance.
            repo_root: Optional workspace root directory.
        """
        self._client = client
        self._repo_root = repo_root or get_repo_root()

    def _publish_single(
        self,
        pkg: PackageMetadata,
        target_dist: Path,
        token: str | None,
        delay: float,
        skip_existing: bool,
    ) -> PackagePublishResult:
        """Publish a single package and return outcome result."""
        if skip_existing and self._client.check_version_exists(pkg.name, pkg.version):
            return PackagePublishResult(
                package=pkg,
                outcome="skipped",
                is_success=False,
                detail="Already on PyPI",
            )

        dist_files = find_package_dist_files(target_dist, pkg)
        if not dist_files:
            return PackagePublishResult(
                package=pkg,
                outcome="failed",
                is_success=False,
                detail="No dist files found",
            )

        is_success, outcome = self._client.publish_package(dist_files, token=token)
        if is_success:
            if delay > 0:
                time.sleep(delay)
            return PackagePublishResult(
                package=pkg, outcome="published", is_success=True
            )
        if outcome == "already_exists":
            return PackagePublishResult(
                package=pkg,
                outcome="skipped",
                is_success=False,
                detail="Already Exists",
            )
        if outcome == "rate_limited":
            return PackagePublishResult(
                package=pkg,
                outcome="failed",
                is_success=False,
                detail="Rate Limited (429)",
            )
        return PackagePublishResult(
            package=pkg,
            outcome="failed",
            is_success=False,
            detail="Upload Failed",
        )

    def handle(self, command: PublishPackagesCommand) -> PyPiPublishReport:
        """Handle PublishPackagesCommand.

        Args:
            command: PublishPackagesCommand specifying publish options.

        Returns:
            PyPiPublishReport summarizing publication outcomes.
        """
        target_dist = command.dist_dir or (self._repo_root / "dist")
        auth_token = (
            command.token
            or os.environ.get("UV_PUBLISH_TOKEN")
            or os.environ.get("PYPI_TOKEN")
        )

        packages = (
            list(command.packages)
            if command.packages is not None
            else discover_workspace_packages(self._repo_root)
        )
        if command.package_name:
            packages = [p for p in packages if p.name == command.package_name]

        if command.build_first:
            for pkg in packages:
                ok, _ = self._client.build_package(pkg.name, target_dist)
                if not ok:
                    return PyPiPublishReport(
                        results=(
                            PackagePublishResult(
                                package=pkg,
                                outcome="failed",
                                is_success=False,
                                detail="Build failed before publish",
                            ),
                        )
                    )

        results: list[PackagePublishResult] = []
        for pkg in packages:
            res = self._publish_single(
                pkg=pkg,
                target_dist=target_dist,
                token=auth_token,
                delay=command.delay,
                skip_existing=command.skip_existing,
            )
            results.append(res)

        return PyPiPublishReport(results=tuple(results))


class VerifyReproducibleBuildHandler:
    """Handler verifying byte-for-byte reproducible package distributions."""

    def __init__(self, client: PyPiClientPort, repo_root: Path | None = None) -> None:
        """Initialize handler with PyPI client port and repo root.

        Args:
            client: PyPiClientPort adapter instance.
            repo_root: Optional workspace root directory.
        """
        self._client = client
        self._repo_root = repo_root or get_repo_root()

    def _compare_package_artifacts(
        self,
        pkg: PackageMetadata,
        p1: Path,
        p2: Path,
    ) -> list[ReproducibleArtifactResult]:
        """Compare built artifacts between two isolated directories."""
        pkg_files_1 = find_package_dist_files(p1, pkg)
        if not pkg_files_1:
            return [
                ReproducibleArtifactResult(
                    package_name=pkg.name,
                    artifact_name="*",
                    hash1="",
                    hash2="",
                    is_reproducible=False,
                )
            ]

        results: list[ReproducibleArtifactResult] = []
        for f1 in pkg_files_1:
            f2 = p2 / f1.name
            if not f2.is_file():
                results.append(
                    ReproducibleArtifactResult(
                        package_name=pkg.name,
                        artifact_name=f1.name,
                        hash1="missing",
                        hash2="missing",
                        is_reproducible=False,
                    )
                )
                continue

            h1 = hashlib.sha256(f1.read_bytes()).hexdigest()
            h2 = hashlib.sha256(f2.read_bytes()).hexdigest()
            results.append(
                ReproducibleArtifactResult(
                    package_name=pkg.name,
                    artifact_name=f1.name,
                    hash1=h1,
                    hash2=h2,
                    is_reproducible=(h1 == h2),
                )
            )
        return results

    def handle(
        self, command: VerifyReproducibleBuildCommand
    ) -> ReproducibleBuildReport:
        """Handle VerifyReproducibleBuildCommand.

        Args:
            command: VerifyReproducibleBuildCommand specifying epoch and package filter.

        Returns:
            ReproducibleBuildReport summarizing byte-for-byte equality of artifacts.
        """
        epoch = (
            command.source_date_epoch
            or os.environ.get("SOURCE_DATE_EPOCH")
            or self._client.get_git_commit_epoch()
            or "1700000000"
        )
        packages = (
            list(command.packages)
            if command.packages is not None
            else discover_workspace_packages(self._repo_root)
        )
        if command.package_name:
            packages = [p for p in packages if p.name == command.package_name]

        all_results: list[ReproducibleArtifactResult] = []

        with (
            tempfile.TemporaryDirectory(prefix="repro_run1_") as t1,
            tempfile.TemporaryDirectory(prefix="repro_run2_") as t2,
        ):
            p1 = Path(t1)
            p2 = Path(t2)
            env = {"SOURCE_DATE_EPOCH": epoch}

            for pkg in packages:
                res1_ok, _ = self._client.build_package(pkg.name, p1, env=env)
                res2_ok, _ = self._client.build_package(pkg.name, p2, env=env)

                if not res1_ok or not res2_ok:
                    all_results.append(
                        ReproducibleArtifactResult(
                            package_name=pkg.name,
                            artifact_name="*",
                            hash1="build_error",
                            hash2="build_error",
                            is_reproducible=False,
                        )
                    )
                    continue

                pkg_results = self._compare_package_artifacts(pkg, p1, p2)
                all_results.extend(pkg_results)

        return ReproducibleBuildReport(epoch=epoch, results=tuple(all_results))
