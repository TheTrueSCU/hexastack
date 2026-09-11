"""Ports defining abstract contracts for PyPI distribution builds, checks, and publishing.

Notes/Architectural Intent:
    Decouples package building (uv build), remote index availability queries (PyPI HTTP),
    publishing (uv publish), and multi-format reporting from domain handlers and driving CLI tools.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path
from typing import Protocol, runtime_checkable

from hexastack_tools.domain.pypi import (
    PyPiBuildReport,
    PyPiCheckReport,
    PyPiPublishReport,
    ReproducibleBuildReport,
)

__all__ = [
    "PyPiClientPort",
    "PyPiPresenterPort",
]


@runtime_checkable
class PyPiClientPort(Protocol):
    """Port interface for querying PyPI index, building wheels, and publishing releases."""

    def check_version_exists(self, package_name: str, version: str) -> bool:
        """Check if a specific package version is already released on PyPI.

        Args:
            package_name: Name of the distribution package.
            version: Version string to check.

        Returns:
            True if version exists on PyPI, False otherwise.
        """

    def build_package(
        self,
        package_name: str,
        out_dir: Path,
        env: dict[str, str] | None = None,
    ) -> tuple[bool, str]:
        """Build distribution package artifacts (wheel and sdist).

        Args:
            package_name: Name of workspace package to build.
            out_dir: Destination directory for built artifacts.
            env: Optional environment variables dictionary (e.g. SOURCE_DATE_EPOCH).

        Returns:
            Tuple of (success: bool, output: str).
        """

    def publish_package(
        self,
        files: list[Path],
        token: str | None = None,
    ) -> tuple[bool, str]:
        """Publish distribution artifacts to PyPI.

        Args:
            files: List of file paths to upload.
            token: Optional PyPI API upload token.

        Returns:
            Tuple of (success: bool, outcome_or_error: str).
        """

    def get_git_commit_epoch(self) -> str | None:
        """Fetch latest git commit timestamp for reproducible build timestamping.

        Returns:
            Epoch string or None if not accessible.
        """


class PyPiPresenterPort(ABC):
    """Abstract port interface for presenting PyPI build, check, and publish diagnostics."""

    @abstractmethod
    def present_check(self, report: PyPiCheckReport) -> int:
        """Render package release availability status table.

        Args:
            report: PyPiCheckReport domain model.

        Returns:
            Exit code (0 for success).
        """

    @abstractmethod
    def present_build(self, report: PyPiBuildReport) -> int:
        """Render package distribution build report.

        Args:
            report: PyPiBuildReport domain model.

        Returns:
            Exit code (0 if all built successfully, 1 if failures occurred).
        """

    @abstractmethod
    def present_publish(self, report: PyPiPublishReport) -> int:
        """Render package publication report.

        Args:
            report: PyPiPublishReport domain model.

        Returns:
            Exit code (0 if all uploads succeeded or were skipped, 1 if failures occurred).
        """

    @abstractmethod
    def present_reproducible(self, report: ReproducibleBuildReport) -> int:
        """Render byte-for-byte reproducible build audit report.

        Args:
            report: ReproducibleBuildReport domain model.

        Returns:
            Exit code (0 if all artifacts matched byte-for-byte, 1 otherwise).
        """
