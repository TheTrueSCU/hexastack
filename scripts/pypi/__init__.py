"""PyPI build, verification, and release tooling package.

Notes/Architectural Intent:
    Provides automated multi-package monorepo distribution building, PyPI API checking,
    and release dry-run verification.
"""

from __future__ import annotations

from scripts.pypi._common import (
    PackageMetadata,
    check_pypi_version_exists,
    get_workspace_packages_metadata,
)
from scripts.pypi.build import build_all_packages
from scripts.pypi.check import check_packages_release_status
from scripts.pypi.publish import publish_packages

__all__ = [
    "PackageMetadata",
    "build_all_packages",
    "check_packages_release_status",
    "check_pypi_version_exists",
    "get_workspace_packages_metadata",
    "publish_packages",
]
