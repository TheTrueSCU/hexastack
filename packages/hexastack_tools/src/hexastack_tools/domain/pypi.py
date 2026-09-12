"""Domain models and CQRS commands for PyPI distribution builds, checks, and publishing.

Notes/Architectural Intent:
    Encapsulates immutable models and commands for monorepo package discovery,
    PyPI release availability checks, distribution building, smart rate-limited
    publishing, and OpenSSF byte-for-byte reproducible build verification.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from hexastack_core.domain.command import Command

__all__ = [
    "BuildPackagesCommand",
    "CheckPyPiReleasesCommand",
    "PackageBuildResult",
    "PackageMetadata",
    "PackagePublishResult",
    "PackageReleaseCheck",
    "PublishPackagesCommand",
    "PyPiBuildReport",
    "PyPiCheckReport",
    "PyPiPublishReport",
    "ReproducibleArtifactResult",
    "ReproducibleBuildReport",
    "VerifyReproducibleBuildCommand",
]


@dataclass(frozen=True)
class PackageMetadata:
    """Metadata for a discovered monorepo subpackage."""

    name: str
    version: str
    dir_path: Path
    pyproject_path: Path


@dataclass(frozen=True)
class PackageReleaseCheck:
    """Release status check for a single package against PyPI index."""

    package: PackageMetadata
    exists: bool


@dataclass(frozen=True)
class PyPiCheckReport:
    """Aggregated report of PyPI release availability checks."""

    checks: tuple[PackageReleaseCheck, ...] = ()


@dataclass(frozen=True)
class PackageBuildResult:
    """Outcome of building distribution packages for a single workspace package."""

    package: PackageMetadata
    success: bool
    output: str = ""


@dataclass(frozen=True)
class PyPiBuildReport:
    """Aggregated report of package distribution build operations."""

    target_dist: Path
    results: tuple[PackageBuildResult, ...] = ()

    @property
    def has_failure(self) -> bool:
        """Return True if any package build failed."""
        return any(not r.success for r in self.results)


@dataclass(frozen=True)
class PackagePublishResult:
    """Outcome of attempting to publish a single package to PyPI."""

    package: PackageMetadata
    outcome: str  # 'published', 'skipped', 'failed'
    is_success: bool
    detail: str = ""


@dataclass(frozen=True)
class PyPiPublishReport:
    """Aggregated report of PyPI package publishing operations."""

    results: tuple[PackagePublishResult, ...] = ()

    @property
    def counts(self) -> dict[str, int]:
        """Return counts of published, skipped, and failed packages."""
        summary = {"published": 0, "skipped": 0, "failed": 0}
        for r in self.results:
            summary[r.outcome] = summary.get(r.outcome, 0) + 1
        return summary

    @property
    def has_failure(self) -> bool:
        """Return True if any package upload failed fatally."""
        return any(not r.is_success and r.outcome != "skipped" for r in self.results)


@dataclass(frozen=True)
class ReproducibleArtifactResult:
    """Reproducibility comparison result for a single distribution artifact."""

    package_name: str
    artifact_name: str
    hash1: str
    hash2: str
    is_reproducible: bool


@dataclass(frozen=True)
class ReproducibleBuildReport:
    """Aggregated report verifying byte-for-byte reproducible builds."""

    epoch: str
    results: tuple[ReproducibleArtifactResult, ...] = ()

    @property
    def all_matched(self) -> bool:
        """Return True if all artifacts matched byte-for-byte."""
        return bool(self.results) and all(r.is_reproducible for r in self.results)


# CQRS Commands


class CheckPyPiReleasesCommand(Command):
    """Command requesting verification of package release availability on PyPI."""

    package_name: str | None = None
    packages: tuple[PackageMetadata, ...] | None = None


class BuildPackagesCommand(Command):
    """Command requesting distribution packaging for workspace packages."""

    target_dist: Path | None = None
    package_name: str | None = None
    packages: tuple[PackageMetadata, ...] | None = None


class PublishPackagesCommand(Command):
    """Command requesting publication of workspace packages to PyPI."""

    dist_dir: Path | None = None
    token: str | None = None
    delay: float = 2.0
    skip_existing: bool = True
    package_name: str | None = None
    packages: tuple[PackageMetadata, ...] | None = None
    build_first: bool = False


class VerifyReproducibleBuildCommand(Command):
    """Command requesting byte-for-byte reproducible build audit."""

    package_name: str | None = None
    packages: tuple[PackageMetadata, ...] | None = None
    source_date_epoch: str | None = None
